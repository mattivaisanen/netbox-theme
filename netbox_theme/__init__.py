"""
Colors, logos and fonts for NetBox's web UI, set by admins for every user.

Admins pick a preset or set each color for light and dark mode under
*Plugins → Theme*, with a live preview, and upload a logo. The theme is one
database row (models.Theme); without it NetBox looks exactly as shipped.
Every page gets the theme's CSS variables in its <head> (template_content.py).
See DEVELOPER.md for how the colors map onto NetBox's CSS.
"""
from netbox.plugins import PluginConfig


class ThemeConfig(PluginConfig):
    name = 'netbox_theme'
    verbose_name = 'Theme'
    description = "Colors, logos and fonts for NetBox's web UI, set by admins for every user."
    version = '0.1.0'
    author = 'Matti'
    base_url = 'theme'
    # Only claim what CI tests (.github/workflows/test.yml).
    min_version = '4.7.0'

    default_settings = {
        # Largest logo file accepted, in kilobytes.
        'max_logo_kb': 512,
        # Largest font file accepted, in kilobytes.
        'max_font_kb': 2048,
    }

    menu_items = 'navigation.menu_items'
    template_extensions = 'template_content.template_extensions'

    def ready(self):
        super().ready()
        from . import custom_colors, statuses

        custom_colors.install()
        statuses.install()


config = ThemeConfig
