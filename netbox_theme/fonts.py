"""
Fonts: uploaded font files and the typography settings that use them.

Font files (models.FontFile) are stored in the database like logos and served
by views.FontView. Their family, weight and style are read from the file
(the `name`, `OS/2`, `head` and `fvar` tables of TrueType/OpenType and WOFF
files) so uploading is all most people need to do. WOFF2 tables are Brotli
compressed, which Python cannot read without an extra package, so for WOFF2
they are guessed from the file name (`Inter-SemiBoldItalic.woff2`); the
editor lets anyone correct them.

Typography (Theme.typography) picks a family for each role (body text,
headings, monospace) and the finer settings a designer would want. Each
setting becomes a `--nbt-*` CSS variable; inc/theme.css falls back to
NetBox's own value for every variable that is not set.
"""
import re
import struct
import zlib

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .css import css_string
from .settings import get_setting

# Format: (sniffed magic, MIME type, CSS format()).
FORMATS = {
    'woff2': ('font/woff2', 'woff2'),
    'woff': ('font/woff', 'woff'),
    'ttf': ('font/ttf', 'truetype'),
    'otf': ('font/otf', 'opentype'),
}
MAX_FILES = 40
WEIGHTS = (100, 200, 300, 400, 500, 600, 700, 800, 900)
STYLES = ('normal', 'italic')

# Families everyone has, offered next to uploaded ones: (key, label, CSS stack).
SYSTEM_FAMILIES = (
    ('system', _('System sans-serif'),
     'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'),
    ('serif', _('System serif'), 'Georgia, Cambria, "Times New Roman", serif'),
    ('system-mono', _('System monospace'),
     'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'),
)
_GENERIC = {'body': 'sans-serif', 'headings': 'sans-serif', 'mono': 'monospace'}
ROLES = (
    ('body', _('Body text')),
    ('headings', _('Headings')),
    ('mono', _('Monospace (code, configs)')),
)

# Typography settings: key -> (default, kind, min, max). A default of '' means
# "NetBox's own" (nothing is set). Sizes in px, spacing in em.
SETTINGS = {
    'body_family': ('', 'family', None, None),
    'headings_family': ('', 'family', None, None),
    'mono_family': ('', 'family', None, None),
    'base_size': (14, 'number', 11, 20),
    'line_height': (1.43, 'number', 1.0, 2.2),
    'body_weight': (400, 'weight', None, None),
    'bold_weight': (600, 'weight', None, None),
    'headings_weight': (600, 'weight', None, None),
    'letter_spacing': (0.0, 'number', -0.05, 0.2),
    'headings_letter_spacing': (0.0, 'number', -0.05, 0.3),
    'headings_case': ('none', 'choice', ('none', 'uppercase'), None),
    'tabular_numbers': (False, 'bool', None, None),
}


# --- Reading font files ----------------------------------------------------

def sniff(data):
    """The font format of `data` ('woff2', 'woff', 'ttf', 'otf') or None."""
    head = data[:4]
    if head == b'wOF2':
        return 'woff2'
    if head == b'wOFF':
        return 'woff'
    if head == b'OTTO':
        return 'otf'
    if head in (b'\x00\x01\x00\x00', b'true'):
        return 'ttf'
    return None


def _tables(data, fmt):
    """{tag: bytes} of an sfnt (TTF/OTF) or WOFF file's tables."""
    tables = {}
    if fmt == 'woff':
        count = struct.unpack_from('>H', data, 12)[0]
        for i in range(count):
            tag, offset, comp_length, orig_length, _checksum = struct.unpack_from('>4sIIII', data, 44 + 20 * i)
            raw = data[offset:offset + comp_length]
            tables[tag.decode('latin-1')] = zlib.decompress(raw) if comp_length < orig_length else raw
    else:
        count = struct.unpack_from('>H', data, 4)[0]
        for i in range(count):
            tag, _checksum, offset, length = struct.unpack_from('>4sIII', data, 12 + 16 * i)
            tables[tag.decode('latin-1')] = data[offset:offset + length]
    return tables


def _family_name(table):
    """Typographic family (name ID 16), else family (ID 1); Windows names first."""
    _format, count, string_offset = struct.unpack_from('>HHH', table, 0)
    found = {}
    for i in range(count):
        platform, _encoding, _language, name_id, length, offset = struct.unpack_from('>HHHHHH', table, 6 + 12 * i)
        if name_id not in (1, 16) or platform not in (1, 3):
            continue
        raw = table[string_offset + offset:string_offset + offset + length]
        text = raw.decode('utf-16-be' if platform == 3 else 'latin-1', errors='replace').strip()
        if text and (name_id, 3) not in found:
            found[(name_id, platform)] = text
    for key in ((16, 3), (16, 1), (1, 3), (1, 1)):
        if key in found:
            return found[key]
    return ''


def _from_tables(data, fmt):
    tables = _tables(data, fmt)
    info = {'variable': 'fvar' in tables}
    if 'name' in tables:
        info['family'] = _family_name(tables['name'])
    if 'OS/2' in tables and len(tables['OS/2']) >= 64:
        weight = struct.unpack_from('>H', tables['OS/2'], 4)[0]
        info['weight'] = min(WEIGHTS, key=lambda w: abs(w - weight))
        info['style'] = 'italic' if struct.unpack_from('>H', tables['OS/2'], 62)[0] & 1 else 'normal'
    elif 'head' in tables and len(tables['head']) >= 46:
        info['style'] = 'italic' if struct.unpack_from('>H', tables['head'], 44)[0] & 2 else 'normal'
    return info


_WEIGHT_WORDS = (
    ('extralight', 200), ('ultralight', 200), ('semibold', 600), ('demibold', 600), ('extrabold', 800),
    ('ultrabold', 800), ('thin', 100), ('hairline', 100), ('light', 300), ('regular', 400), ('normal', 400),
    ('book', 400), ('medium', 500), ('bold', 700), ('black', 900), ('heavy', 900),
)


def _from_filename(filename):
    """Family, weight and style guessed from a name like `Open_Sans-SemiBoldItalic.woff2`."""
    stem = re.sub(r'\.[^.]+$', '', filename or '')
    stem = re.sub(r'\[[^\]]*\]', ' variable ', stem)
    family, _sep, rest = stem.partition('-')
    words = (rest or '').lower().replace('_', '').replace(' ', '')
    weight = next((value for word, value in _WEIGHT_WORDS if word in words), 400)
    family = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', family.replace('_', ' ')).strip()
    family = re.sub(r'\s*variable\s*', ' ', family, flags=re.I).strip()
    return {
        'family': family or 'Custom font',
        'weight': weight,
        'style': 'italic' if 'italic' in words or 'oblique' in words else 'normal',
        'variable': 'variable' in stem.lower(),
    }


def read(data, filename=''):
    """
    {format, family, weight, style, variable} of an uploaded font file.
    Raises ValidationError for anything that is not a font we accept.
    """
    limit = get_setting('max_font_kb')
    if len(data) > limit * 1024:
        raise ValidationError(_('{name}: larger than {kb} KB.').format(name=filename, kb=limit))
    fmt = sniff(data)
    if fmt is None:
        raise ValidationError(_('{name}: not a WOFF2, WOFF, TTF or OTF font.').format(name=filename))
    info = _from_filename(filename)
    if fmt != 'woff2':
        try:
            info.update({key: value for key, value in _from_tables(data, fmt).items() if value or key == 'variable'})
        except (struct.error, zlib.error, ValueError):
            pass  # A font browsers can still use; the file name guess stands.
    info['format'] = fmt
    info['family'] = clean_family(info['family'])
    return info


def clean_family(name):
    name = ' '.join(str(name or '').split())[:60]
    if not name:
        raise ValidationError(_('Every font needs a family name.'))
    return name


# --- Typography settings ------------------------------------------------------

def family_choices(families):
    """[(value, label, CSS stack)] for a family select; '' (NetBox's) comes first in the template."""
    choices = [(key, label, stack) for key, label, stack in SYSTEM_FAMILIES]
    choices += [(f'font:{family}', family, None) for family in families]
    return choices


def stack(value, role):
    """The CSS font-family list for a family setting, or '' for NetBox's."""
    if not value:
        return ''
    for key, _label, system_stack in SYSTEM_FAMILIES:
        if value == key:
            return system_stack
    if value.startswith('font:'):
        return f'{css_string(value[5:])}, {_GENERIC[role]}'
    return ''


def clean_typography(values, families):
    """Validated typography settings; missing ones get their default. Raises ValidationError."""
    if not isinstance(values, dict):
        raise ValidationError(_('Typography must be an object.'))
    allowed_families = {''} | {key for key, _label, _stack in SYSTEM_FAMILIES} | {f'font:{f}' for f in families}
    cleaned = {}
    for key, (default, kind, low, high) in SETTINGS.items():
        value = values.get(key, default)
        if kind == 'family':
            if value not in allowed_families:
                raise ValidationError(_('Unknown font family: {value}').format(value=value))
        elif kind == 'number':
            try:
                value = round(float(value), 3)
            except (TypeError, ValueError):
                raise ValidationError(_('{key} must be a number.').format(key=key))
            if not low <= value <= high:
                raise ValidationError(_('{key} must be between {low} and {high}.').format(key=key, low=low, high=high))
        elif kind == 'weight':
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValidationError(_('{key} must be a weight.').format(key=key))
            if value not in WEIGHTS:
                raise ValidationError(_('{key} must be a weight from 100 to 900.').format(key=key))
        elif kind == 'choice':
            if value not in low:
                raise ValidationError(_('{key}: unknown value.').format(key=key))
        elif kind == 'bool':
            value = value in (True, 'on', 'true', '1', 1)
        cleaned[key] = value
    return cleaned


def with_defaults(typography):
    """Every setting, the saved value or its default."""
    saved = typography if isinstance(typography, dict) else {}
    return {key: saved.get(key, default) for key, (default, *_rest) in SETTINGS.items()}


def css_variables(typography):
    """`--nbt-*` font variables for settings that differ from NetBox's."""
    t = with_defaults(typography)
    defaults = {key: default for key, (default, *_rest) in SETTINGS.items()}
    out = {}
    for role in ('body', 'headings', 'mono'):
        family = stack(t[f'{role}_family'], role)
        if family:
            out[f'--nbt-font-{role}'] = family
    if t['base_size'] != defaults['base_size']:
        out['--nbt-font-size'] = f"{t['base_size'] / 16:.4f}rem"
    if t['line_height'] != defaults['line_height']:
        out['--nbt-line-height'] = f"{t['line_height']}"
    for key in ('body_weight', 'bold_weight', 'headings_weight'):
        if t[key] != defaults[key]:
            out[f"--nbt-{key.replace('_', '-')}"] = str(t[key])
    if t['letter_spacing']:
        out['--nbt-letter-spacing'] = f"{t['letter_spacing']}em"
    if t['headings_letter_spacing']:
        out['--nbt-headings-letter-spacing'] = f"{t['headings_letter_spacing']}em"
    if t['headings_case'] != 'none':
        out['--nbt-headings-case'] = t['headings_case']
    if t['tabular_numbers']:
        out['--nbt-numbers'] = 'tabular-nums'
    return out


def font_faces(fonts, url_for):
    """@font-face rules for FontFile rows (data not needed)."""
    rules = []
    for font in fonts:
        weight = '100 900' if font.variable else str(font.weight)
        rules.append(
            f'@font-face {{ font-family: {css_string(font.family)}; '
            f'src: url("{url_for(font)}") format("{FORMATS[font.format][1]}"); '
            f'font-weight: {weight}; font-style: {font.style}; font-display: swap; }}'
        )
    return ' '.join(rules)
