"""
The colors a theme sets, NetBox's own values for them, and the presets.

A theme is one value per token for each mode (light and dark). Every token
becomes a CSS variable `--nbt-<token>` (and `--nbt-<token>-rgb`), which
templates/netbox_theme/inc/theme.css maps onto NetBox's own variables.
"""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

MODES = ('light', 'dark')

# (group, label, ((token, label), ...)), in the order the editor shows them.
GROUPS = (
    ('brand', _('Brand'), (
        ('primary', _('Primary')),
        ('primary_fg', _('Text on primary')),
        ('link', _('Links')),
    )),
    ('page', _('Page'), (
        ('body_bg', _('Background')),
        ('header', _('Top bar')),
        ('text', _('Text')),
        ('muted', _('Muted text')),
        ('border', _('Borders')),
    )),
    ('content', _('Cards, tables and forms'), (
        ('surface', _('Card background')),
        ('card_header', _('Card header')),
        ('table_header', _('Table header')),
        ('table_header_text', _('Table header text')),
        ('input_bg', _('Form fields')),
    )),
    ('sidebar', _('Sidebar'), (
        ('sidebar', _('Background')),
        ('sidebar_text', _('Text')),
        ('sidebar_accent', _('Headings and accent')),
    )),
    ('status', _('Status'), (
        ('secondary', _('Secondary')),
        ('success', _('Success')),
        ('info', _('Info')),
        ('warning', _('Warning')),
        ('danger', _('Danger')),
    )),
    # NetBox's object action buttons, drawn in fixed named colors (inc/theme.css).
    ('buttons', _('Buttons'), (
        ('button_clone', _('Clone')),
        ('button_edit', _('Edit')),
        ('button_delete', _('Delete')),
        ('button_import', _('Import and bookmark')),
        ('button_export', _('Export')),
    )),
    # Create / Update / Delete badges in the changelog and change requests (actions.py).
    ('actions', _('Change actions'), (
        ('action_create', _('Create')),
        ('action_update', _('Update')),
        ('action_delete', _('Delete')),
    )),
)
TOKENS = tuple(token for _group, _label, tokens in GROUPS for token, _label in tokens)

_STATUS = {
    'secondary': '#6b7280', 'success': '#2fb344', 'info': '#4299e1', 'warning': '#f59f00', 'danger': '#d63939',
}
# NetBox's green, yellow, red, cyan and purple, the same in both modes.
_BUTTONS = {
    'button_clone': '#2fb344', 'button_edit': '#f59f00', 'button_delete': '#d63939',
    'button_import': '#17a2b8', 'button_export': '#ae3ec9',
    # NetBox's green, blue and red for changelog actions.
    'action_create': '#2fb344', 'action_update': '#066fd1', 'action_delete': '#d63939',
}

# NetBox 4.7's own colors (netbox.css), so a fresh theme starts where NetBox is.
NETBOX = {
    'light': {
        **_STATUS, **_BUTTONS,
        'primary': '#00857d', 'primary_fg': '#f9fafb', 'link': '#00857d',
        'body_bg': '#f9fafb', 'header': '#ffffff', 'text': '#374151', 'muted': '#6b7280', 'border': '#e5e7eb',
        'surface': '#ffffff', 'card_header': '#f9fafb', 'table_header': '#f9fafb', 'table_header_text': '#6b7280',
        'input_bg': '#ffffff',
        'sidebar': '#ffffff', 'sidebar_text': '#001423', 'sidebar_accent': '#00857d',
    },
    'dark': {
        **_STATUS, **_BUTTONS,
        'secondary': '#9ca3af',
        'primary': '#00f2d4', 'primary_fg': '#001423', 'link': '#00f2d4',
        'body_bg': '#081b2a', 'header': '#001423', 'text': '#e5e7eb', 'muted': '#9ca3af', 'border': '#374151',
        'surface': '#001423', 'card_header': '#1f2937', 'table_header': '#001423', 'table_header_text': '#9ca3af',
        'input_bg': '#111827',
        'sidebar': '#001423', 'sidebar_text': '#ffffff', 'sidebar_accent': '#00f2d4',
    },
}


def _mix(color, other, share):
    """`share` (0..1) of `other` mixed into `color`, both #rrggbb."""
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * share):02x}' for x, y in zip(a, b))


# Button and change action colors follow the status color closest to them, so
# a theme saved before they existed recolors them too. Export (purple) and
# Update (blue) have no match.
_BUTTONS_DERIVED = {
    'button_clone': ('success', None), 'button_edit': ('warning', None), 'button_delete': ('danger', None),
    'button_import': ('info', None), 'action_create': ('success', None), 'action_delete': ('danger', None),
}

# Colors added after the first version follow the ones they used to share, so
# older themes and imports keep their look: {mode: {token: (source, mix)}}.
# `mix` is (other token, share) to blend in, or None to copy the source.
_DERIVED = {
    'light': {
        'header': ('surface', None), 'input_bg': ('surface', None), 'card_header': ('body_bg', None),
        'table_header': ('body_bg', None), 'table_header_text': ('muted', None), **_BUTTONS_DERIVED,
    },
    'dark': {
        'header': ('surface', None), 'table_header': ('surface', None), 'table_header_text': ('muted', None),
        'card_header': ('surface', ('text', 0.08)), 'input_bg': ('body_bg', None), **_BUTTONS_DERIVED,
    },
}


def _preset(light, dark):
    return {'light': complete(light, 'light'), 'dark': complete(dark, 'dark')}


def _accent(light, dark, **dark_page):
    """A preset that only changes the accent color and the dark page tones."""
    return _preset(
        {'primary': light, 'link': light, 'sidebar_accent': light},
        {'primary': dark, 'link': dark, 'sidebar_accent': dark, **dark_page},
    )


HEX = re.compile(r'^#[0-9a-fA-F]{6}$')


def is_color(value):
    return isinstance(value, str) and bool(HEX.match(value))


def rgb(value):
    """'#00857d' -> '0, 133, 125' (for NetBox's `-rgb` variables)."""
    return ', '.join(str(int(value[i:i + 2], 16)) for i in (1, 3, 5))


def complete(colors, mode):
    """
    Every token for `mode`: valid values from `colors`; a missing one derived
    from those it follows (_DERIVED) when they are given, else NetBox's.
    """
    colors = colors if isinstance(colors, dict) else {}
    given = {token: colors[token].lower() for token in TOKENS if is_color(colors.get(token))}
    for token, (source, mix) in _DERIVED[mode].items():
        if token not in given and source in given:
            if mix is None:
                given[token] = given[source]
            else:
                other = given.get(mix[0], NETBOX[mode][mix[0]])
                given[token] = _mix(given[source], other, mix[1])
    return {token: given.get(token, NETBOX[mode][token]) for token in TOKENS}


def validate(colors, mode):
    """Like complete(), but a value that is there and not a #rrggbb color is an error."""
    if not isinstance(colors, dict):
        raise ValidationError(_('{mode}: expected an object of colors.').format(mode=mode))
    bad = sorted(token for token in TOKENS if token in colors and not is_color(colors[token]))
    if bad:
        raise ValidationError(
            _('{mode}: not a #rrggbb color: {tokens}').format(mode=mode, tokens=', '.join(bad))
        )
    return complete(colors, mode)


# (slug, label, colors). Slugs are stable: exports name the preset they came from.
PRESETS = (
    ('netbox', _('NetBox'), NETBOX),
    ('ocean', _('Ocean'), _accent(
        '#0b63c5', '#5aa9ff', primary_fg='#04172e', body_bg='#0a1220', surface='#0d1b2e', sidebar='#0d1b2e',
        border='#1e3350',
    )),
    ('forest', _('Forest'), _accent(
        '#2f7d32', '#6fcf73', primary_fg='#0b1f0c', body_bg='#0c1410', surface='#112018', sidebar='#112018',
        border='#22372b',
    )),
    ('sunset', _('Sunset'), _accent(
        '#d9480f', '#ff8a4c', primary_fg='#2a0f02', body_bg='#16100d', surface='#231610', sidebar='#231610',
        border='#3b2a20',
    )),
    ('royal', _('Royal'), _accent(
        '#6741d9', '#a78bfa', primary_fg='#1a1033', body_bg='#110f1f', surface='#1a1530', sidebar='#1a1530',
        border='#2e2850',
    )),
    ('graphite', _('Graphite'), _preset(
        {'primary': '#374151', 'link': '#1f2937', 'sidebar_accent': '#374151', 'sidebar_text': '#111827'},
        {'primary': '#d1d5db', 'primary_fg': '#111827', 'link': '#e5e7eb', 'sidebar_accent': '#d1d5db',
         'surface': '#1f2937', 'sidebar': '#1f2937'},
    )),
    ('navy', _('Navy sidebar'), _preset(
        {'primary': '#1e40af', 'link': '#1d4ed8', 'sidebar': '#0f172a', 'sidebar_text': '#e2e8f0',
         'sidebar_accent': '#60a5fa'},
        {'primary': '#60a5fa', 'primary_fg': '#0f172a', 'link': '#60a5fa', 'sidebar_accent': '#60a5fa',
         'body_bg': '#0b1120', 'surface': '#0f172a', 'sidebar': '#0b1222', 'border': '#1e293b'},
    )),
)

DARK_TEXT, LIGHT_TEXT = '#111827', '#ffffff'


def readable_text(value):
    """Dark or white text, whichever reads better on `value` (WCAG contrast)."""
    def channel(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(value[i:i + 2], 16) for i in (1, 3, 5))
    luminance = 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
    # Contrast with white is 1.05 / (L + .05), with #111827 (L ~ .0103) (L + .05) / .0603.
    return DARK_TEXT if (luminance + 0.05) / 0.0603 > 1.05 / (luminance + 0.05) else LIGHT_TEXT


def css_variables(colors):
    """
    `--nbt-<token>: #hex; --nbt-<token>-rgb: r, g, b; --nbt-<token>-on: #hex;`
    for every token. `-on` is the text color for that color as a background.
    The editor's script computes the same (theme.html).
    """
    lines = []
    for token in TOKENS:
        name, value = token.replace('_', '-'), colors[token]
        lines.append(f'--nbt-{name}: {value}; --nbt-{name}-rgb: {rgb(value)}; --nbt-{name}-on: {readable_text(value)};')
    return ' '.join(lines)
