"""
Theme files: export the saved theme as JSON and import one back.

    {"netbox_theme": 1, "name": "...", "light": {token: "#rrggbb"},
     "dark": {...}, "logo_light": "data:...", "logo_dark": "data:...",
     "logo_login_light": "data:...", "logo_login_dark": "data:...",
     "edition": "netbox" | "hidden" | "custom", "edition_text": "...",
     "logo_height": 32, "logo_margin_top": 12, "logo_margin_bottom": 12,
     "custom_colors": [{"slug", "name", "light", "dark"}, ...],
     "status_colors": {"active": "green" | "nbt-<slug>", ...}}

Imports are checked like the editor's input: colors must be #rrggbb (unknown
tokens are ignored, missing ones get NetBox's color) and logos are re-checked
as uploads. A logo the file leaves out or empty keeps the current one.
"""
import json

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from . import colors, custom_colors, logos, statuses
from .models import EditionChoices, Theme

FORMAT = 1
MAX_FILE_BYTES = 8 * 1024 * 1024


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
    }


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
