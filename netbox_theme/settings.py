"""Plugin settings: PLUGINS_CONFIG['netbox_theme'], with defaults from
ThemeConfig.default_settings."""
from netbox.plugins.utils import get_plugin_config

PLUGIN = 'netbox_theme'


def get_setting(key):
    return get_plugin_config(PLUGIN, key)
