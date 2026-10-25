# Configuration

Settings go in NetBox's `configuration.py`:

```python
PLUGINS_CONFIG = {
    'netbox_theme': {
        'max_logo_kb': 512,
    },
}
```

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `max_logo_kb` | int | `512` | Largest logo file accepted, in kilobytes (uploads and imports). |

Everything else is set under **Plugins → Theme**.

## Permissions

| Permission | Allows |
| --- | --- |
| `netbox_theme.change_theme` | Opening the theme editor, saving, restoring defaults, export and import |

Superusers have it. Everyone sees the saved theme and logo; that needs no
permission.

## Theme files

*Export* downloads `netbox-theme.json`:

```json
{
  "netbox_theme": 1,
  "name": "Ocean",
  "light": {"primary": "#0b63c5", "...": "..."},
  "dark": {"primary": "#5aa9ff", "...": "..."},
  "logo_light": "data:image/svg+xml;base64,...",
  "logo_dark": "",
  "logo_login_light": "",
  "logo_login_dark": "",
  "logo_height": 32,
  "logo_margin_top": 12,
  "logo_margin_bottom": 12,
  "edition": "netbox",
  "edition_text": "",
  "custom_colors": [{"slug": "brand", "name": "Brand", "light": "#0b63c5", "dark": "#5aa9ff"}],
  "status_colors": {"active": "nbt-brand", "planned": "purple"}
}
```

*Import* replaces the saved theme. Colors must be `#rrggbb`; unknown names
are ignored. Missing ones follow the color they were split from in older
versions (top bar and table header from card background, and so on), else
get NetBox's color. Logos are checked like
uploads. `edition` is `netbox`, `hidden` or `custom`. Widget colors keep
their `slug` (dashboard widgets store `nbt-<slug>`); a missing slug is made
from the name. `status_colors` maps a status value to one of NetBox's color
names or `nbt-<slug>`; statuses this NetBox does not have are skipped. The
color names are listed in `netbox_theme/colors.py` (`GROUPS`).
