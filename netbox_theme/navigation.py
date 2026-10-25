from django.utils.translation import gettext_lazy as _

from netbox.plugins import PluginMenuItem

menu_items = (
    PluginMenuItem(
        link='plugins:netbox_theme:theme',
        link_text=_('Theme'),
        permissions=['netbox_theme.change_theme'],
    ),
)
