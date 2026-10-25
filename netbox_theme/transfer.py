"""
Theme files: export the saved theme as JSON and import one back.

    {"netbox_theme": 1, "name": "...", "light": {token: "#rrggbb"},
     "dark": {...}, "logo_light": "data:...", "logo_dark": "data:...",
     "logo_login_light": "data:...", "logo_login_dark": "data:...",
     "edition": "netbox" | "hidden" | "custom", "edition_text": "...",
     "logo_height": 32, "logo_margin_top": 12, "logo_margin_bottom": 12,
     "custom_colors": [{"slug", "name", "light", "dark"}, ...],
     "status_colors": {"active": "green" | "nbt-<slug>", ...},
     "typography": {setting: value}, "fonts": [{"family", "weight", "style",
     "variable", "filename", "data": base64}, ...]}

Imports are checked like the editor's input: colors must be #rrggbb (unknown
tokens are ignored, missing ones get NetBox's color) and logos are re-checked
as uploads, fonts too. A logo the file leaves out or empty keeps the current
one; so do the font files when the file has no `fonts` list.
"""
import base64
import binascii
import json

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from . import colors, custom_colors, fonts, logos, statuses
from .models import EditionChoices, FontFile, Theme

FORMAT = 1
# Room for every font file at the largest size, base64 encoded.
MAX_FILE_BYTES = 128 * 1024 * 1024


def dump(theme):
    return {
        'netbox_theme': FORMAT,
        'name': theme.name,
        'light': theme.colors('light'),
        'dark': theme.colors('dark'),
        **{f'logo_{slot}': getattr(theme, f'logo_{slot}') for slot in logos.SLOTS},
        'edition': theme.edition,
        'edition_text': theme.edition_text,
        'logo_height': theme.logo_height,
        'logo_margin_top': theme.logo_margin_top,
        'logo_margin_bottom': theme.logo_margin_bottom,
        'custom_colors': custom_colors.stored(theme),
        'status_colors': statuses.stored(theme),
        'typography': fonts.with_defaults(theme.typography),
        'fonts': [
            {'family': font.family, 'weight': font.weight, 'style': font.style, 'variable': font.variable,
             'filename': font.filename, 'data': base64.b64encode(bytes(font.data)).decode()}
            for font in FontFile.objects.all()
        ],
    }


def load(raw):
    """Theme field values from a theme file's bytes. Raises ValidationError."""
    if len(raw) > MAX_FILE_BYTES:
        raise ValidationError(_('Theme file is too large.'))
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, ValueError):
        raise ValidationError(_('Theme file is not valid JSON.'))
    if not isinstance(data, dict) or data.get('netbox_theme') != FORMAT:
        raise ValidationError(_('Not a NetBox theme file.'))
    name = data.get('name') or 'Imported'
    if not isinstance(name, str):
        raise ValidationError(_('Theme name must be text.'))
    edition = data.get('edition') or EditionChoices.NETBOX
    custom = custom_colors.clean(data.get('custom_colors') or [])
    status_colors = statuses.clean(data.get('status_colors') or {}, {entry['slug'] for entry in custom})
    edition_text = data.get('edition_text') or ''
    if edition not in EditionChoices.values or not isinstance(edition_text, str):
        raise ValidationError(_('Unknown edition label setting.'))
    return {
        'name': name.strip()[:100] or 'Imported',
        'edition': edition,
        'edition_text': edition_text.strip()[:50],
        'light': colors.validate(data.get('light', {}), 'light'),
        'dark': colors.validate(data.get('dark', {}), 'dark'),
        # A file without a logo keeps the current one (themes made by hand or
        # from a palette usually have none); Remove in the editor clears it.
        **{f'logo_{slot}': logos.check_data_uri(data[f'logo_{slot}'])
           for slot in logos.SLOTS if data.get(f'logo_{slot}')},
        **_logo_size(data),
        'custom_colors': custom,
        'status_colors': status_colors,
        **_fonts(data),
    }


def _fonts(data):
    """
    {'fonts': [...], 'typography': {...}}. Without a `fonts` list the file
    keeps the saved font files; typography may only use families it has.
    """
    result = {}
    families = set(FontFile.families())
    if isinstance(data.get('fonts'), list):
        result['fonts'], families = [], set()
        for entry in data['fonts'][:fonts.MAX_FILES]:
            if not isinstance(entry, dict) or not isinstance(entry.get('data'), str):
                raise ValidationError(_('Font entries need their file data.'))
            try:
                raw = base64.b64decode(entry['data'])
            except (binascii.Error, ValueError):
                raise ValidationError(_('A font file is not valid base64.'))
            info = fonts.read(raw, str(entry.get('filename') or ''))
            if entry.get('family'):
                info['family'] = fonts.clean_family(entry['family'])
            if entry.get('weight') in fonts.WEIGHTS:
                info['weight'] = entry['weight']
            if entry.get('style') in fonts.STYLES:
                info['style'] = entry['style']
            info['variable'] = bool(entry.get('variable', info['variable']))
            result['fonts'].append((info, raw, str(entry.get('filename') or '')[:200]))
            families.add(info['family'])
    result['typography'] = fonts.clean_typography(data.get('typography') or {}, families)
    return result


def _logo_size(data):
    """Logo height and spacing; missing ones get the defaults, bad ones are errors."""
    sizes = {}
    for field in ('logo_height', 'logo_margin_top', 'logo_margin_bottom'):
        model_field = Theme._meta.get_field(field)
        value = data.get(field, model_field.default)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValidationError(_('{field} must be a whole number.').format(field=field))
        model_field.run_validators(value)
        sizes[field] = value
    return sizes
