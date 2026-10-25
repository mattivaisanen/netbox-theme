"""Small CSS snippets built from theme settings (see inc/head.html)."""
from django.utils.safestring import mark_safe

from .models import EditionChoices


def css_string(text):
    """
    `text` as a quoted CSS string: everything but letters and digits escaped,
    spaces too (CSS swallows one space after an escape).
    """
    return '"' + ''.join(c if c.isalnum() else f'\\{ord(c):06x}' for c in text) + '"'


def edition(choice, text):
    """
    CSS for the edition label ("Community") under the logo, in the sidebar and
    on the login page. Custom text replaces NetBox's with ::after, so no
    NetBox template is overridden.
    """
    if choice == EditionChoices.HIDDEN:
        return mark_safe('html[data-bs-theme] .netbox-edition { display: none !important; }')
    if choice == EditionChoices.CUSTOM and text:
        return mark_safe(
            'html[data-bs-theme] .netbox-edition { font-size: 0 !important; letter-spacing: normal; }'
            f' html[data-bs-theme] .netbox-edition::after {{ content: {css_string(text)}; font-size: .875rem; }}'
            ' html[data-bs-theme] .navbar-brand .netbox-edition::after { font-size: .75rem; }'
        )
    return ''


def logo_size(height, top, bottom):
    """
    Sidebar logo height and the space above and below it, in pixels (ints,
    validated by the model). Only on wide screens, where the sidebar shows;
    the mobile header keeps NetBox's compact spacing.
    """
    return mark_safe(
        f'html[data-bs-theme] .navbar-brand-image {{ height: {int(height)}px; }}'
        ' @media (min-width: 992px) { html[data-bs-theme] .navbar-vertical.navbar-expand-lg .navbar-brand'
        f' {{ padding-top: {int(top)}px !important; padding-bottom: {int(bottom)}px !important; }} }}'
    )


# NetBox's named colors (dashboard widgets, choice badges). netbox.css puts
# near-white text on all of them, which is hard to read on the light ones.
NETBOX_PALETTE = {
    'blue': '#066fd1', 'azure': '#4299e1', 'indigo': '#4263eb', 'purple': '#ae3ec9', 'pink': '#d6336c',
    'red': '#d63939', 'orange': '#f76707', 'yellow': '#f59f00', 'lime': '#74b816', 'green': '#2fb344',
    'teal': '#0ca678', 'cyan': '#17a2b8', 'gray': '#6b7280',
}


def netbox_palette_text():
    """Dark text on NetBox's named colors where it reads better than white."""
    from .colors import DARK_TEXT, readable_text

    names = [name for name, value in NETBOX_PALETTE.items() if readable_text(value) == DARK_TEXT]
    if not names:
        return ''
    selector = ', '.join(f'html[data-bs-theme] .text-bg-{name}' for name in names)
    return mark_safe(f'{selector} {{ color: {DARK_TEXT} !important; }}')
