"""
Fonts: one font per role (body text, headings, code), each from a few fixed
file slots, plus the typography settings that use them.

NetBox draws text in four styles: regular (400), medium (500: labels,
buttons, menus, table headers), bold (600: headings, strong text) and,
rarely, italic. So body text has a slot for each; headings and code have
one. A slot left empty is drawn from the nearest one by the browser, so
Regular alone is enough; a variable font (one file with every weight) in
Regular covers all of them.

Files (models.FontFile) are stored in the database like logos and served by
views.FontView. Every role's files share one CSS family name (`nbt-<role>`),
so what a file calls its family does not matter; `read()` still reads the
family, weight and style (TrueType/OpenType/WOFF tables, or the file name for
WOFF2, whose tables need Brotli) to show users what they uploaded.

Typography (Theme.typography) picks the source for each role and the finer
settings. Each setting becomes a `--nbt-*` CSS variable; inc/theme.css falls
back to NetBox's own value for every variable that is not set.
"""
import re
import struct
import zlib

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .settings import get_setting

# Format: (MIME type, CSS format()).
FORMATS = {
    'woff2': ('font/woff2', 'woff2'),
    'woff': ('font/woff', 'woff'),
    'ttf': ('font/ttf', 'truetype'),
    'otf': ('font/otf', 'opentype'),
}
WEIGHTS = (100, 200, 300, 400, 500, 600, 700, 800, 900)

ROLES = (
    ('body', _('Body text')),
    ('headings', _('Headings')),
    ('mono', _('Code and configs')),
)
# role -> ((slot, label, CSS font-weight range, font-style), ...). Ranges make
# one file serve neighbouring weights (Regular also draws light text).
SLOTS = {
    'body': (
        ('regular', _('Regular'), '100 449', 'normal'),
        ('medium', _('Medium'), '450 549', 'normal'),
        ('bold', _('Bold'), '550 900', 'normal'),
        ('italic', _('Italic'), '100 900', 'italic'),
    ),
    'headings': (
        ('bold', _('Heading font'), '100 900', 'normal'),
    ),
    'mono': (
        ('regular', _('Regular'), '100 900', 'normal'),
    ),
}
ALL_SLOTS = {(role, slot) for role, slots in SLOTS.items() for slot, *_rest in slots}

# Where a role's text comes from: '' is NetBox's (Inter / Roboto Mono; for
# headings the body font), 'uploaded' the role's own files, or a system font.
SOURCES = {
    'body': (
        ('', _("NetBox's (Inter)")),
        ('uploaded', _('Uploaded font')),
        ('system', _('System sans-serif')),
        ('serif', _('System serif')),
    ),
    'headings': (
        ('', _('Same as body text')),
        ('uploaded', _('Uploaded font')),
        ('system', _('System sans-serif')),
        ('serif', _('System serif')),
    ),
    'mono': (
        ('', _("NetBox's (Roboto Mono)")),
        ('uploaded', _('Uploaded font')),
        ('system-mono', _('System monospace')),
    ),
}
_SYSTEM_STACKS = {
    'system': 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    'serif': 'Georgia, Cambria, "Times New Roman", serif',
    'system-mono': 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
}
_GENERIC = {'body': 'sans-serif', 'headings': 'sans-serif', 'mono': 'monospace'}

# Typography settings: key -> (default, kind, allowed / min, max). Sizes in
# px, spacing in em.
SETTINGS = {
    'body_family': ('', 'source', 'body', None),
    'headings_family': ('', 'source', 'headings', None),
    'mono_family': ('', 'source', 'mono', None),
    'base_size': (14, 'number', 11, 20),
    'line_height': (1.43, 'number', 1.0, 2.2),
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
    {format, family, weight, style, variable} of an uploaded font file (for
    showing users what they uploaded; slots decide how it is used).
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

def family_name(role):
    """The CSS family name a role's uploaded files are declared under."""
    return f'nbt-{role}'


def stack(source, role, uploaded_roles):
    """The CSS font-family list for a role's source, or '' for NetBox's."""
    if source in _SYSTEM_STACKS:
        return _SYSTEM_STACKS[source]
    if source == 'uploaded' and role in uploaded_roles:
        return f'"{family_name(role)}", {_GENERIC[role]}'
    return ''


def clean_typography(values):
    """Validated typography settings; missing ones get their default. Raises ValidationError."""
    if not isinstance(values, dict):
        raise ValidationError(_('Typography must be an object.'))
    cleaned = {}
    for key, (default, kind, low, high) in SETTINGS.items():
        value = values.get(key, default)
        if kind == 'source':
            if value not in {source for source, _label in SOURCES[low]}:
                raise ValidationError(_('Unknown font choice: {value}').format(value=value))
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


def css_variables(typography, uploaded_roles):
    """`--nbt-*` font variables for settings that differ from NetBox's."""
    t = with_defaults(typography)
    defaults = {key: default for key, (default, *_rest) in SETTINGS.items()}
    out = {}
    for role, _label in ROLES:
        family = stack(t[f'{role}_family'], role, uploaded_roles)
        if family:
            out[f'--nbt-font-{role}'] = family
    if t['base_size'] != defaults['base_size']:
        out['--nbt-font-size'] = f"{t['base_size'] / 16:.4f}rem"
    if t['line_height'] != defaults['line_height']:
        out['--nbt-line-height'] = f"{t['line_height']}"
    if t['headings_weight'] != defaults['headings_weight']:
        out['--nbt-headings-weight'] = str(t['headings_weight'])
    if t['letter_spacing']:
        out['--nbt-letter-spacing'] = f"{t['letter_spacing']}em"
    if t['headings_letter_spacing']:
        out['--nbt-headings-letter-spacing'] = f"{t['headings_letter_spacing']}em"
    if t['headings_case'] != 'none':
        out['--nbt-headings-case'] = t['headings_case']
    if t['tabular_numbers']:
        out['--nbt-numbers'] = 'tabular-nums'
    return out


def font_faces(files, url_for):
    """@font-face rules for FontFile rows (data not needed)."""
    slots = {(role, slot): (weights, style) for role, entries in SLOTS.items() for slot, _l, weights, style in entries}
    rules = []
    for font in files:
        if (font.role, font.slot) not in slots:
            continue
        weights, style = slots[(font.role, font.slot)]
        if font.variable and style == 'normal':
            weights = '100 900'
        rules.append(
            f'@font-face {{ font-family: "{family_name(font.role)}"; '
            f'src: url("{url_for(font)}") format("{FORMATS[font.format][1]}"); '
            f'font-weight: {weights}; font-style: {style}; font-display: swap; }}'
        )
    return ' '.join(rules)
