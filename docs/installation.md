# Installation

## Requirements

- NetBox 4.7 (4.7.0 to the latest 4.7 release). NetBox refuses to start the
  plugin on a newer minor release until it has been tested there.
- No other plugins and no extra Python packages.

## Install

1. Install the package into NetBox's Python environment:

   ```bash
   pip install git+https://github.com/mattivaisanen/netbox-theme.git
   ```

   With netbox-docker, add the same line to `plugin_requirements.txt` and
   rebuild the image, or bind-mount a checkout and `pip install -e` it.

2. Enable it in `configuration.py` (netbox-docker: `configuration/plugins.py`):

   ```python
   PLUGINS = ['netbox_theme']
   ```

3. Create the plugin's tables and restart NetBox:

   ```bash
   python manage.py migrate
   ```

The theme editor is then under **Plugins → Theme** for superusers. Until a
theme is saved, NetBox looks exactly as shipped.

## Upgrade

```bash
pip install --upgrade git+https://github.com/mattivaisanen/netbox-theme.git
python manage.py migrate
```

Restart NetBox and read [CHANGELOG.md](../CHANGELOG.md) for anything a
release asks you to do.

## Uninstall

1. Optional: *Export* the theme first if you may want it back.
2. Remove the plugin's tables while it is still enabled. This deletes the
   saved theme, logos and uploaded fonts:

   ```bash
   python manage.py migrate netbox_theme zero
   ```

3. Remove `'netbox_theme'` from `PLUGINS`, uninstall the package and restart
   NetBox:

   ```bash
   pip uninstall netbox-theme
   ```

NetBox's own data is never changed by the plugin, with one exception:
dashboard widgets that use a custom color keep its name (`nbt-<name>`) in
the user's dashboard. Without the plugin they are drawn uncolored; pick a
NetBox color for them under *Configure* to tidy up.
