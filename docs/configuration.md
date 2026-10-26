# Configuration

Settings go in NetBox's `configuration.py`:

```python
PLUGINS_CONFIG = {
    'netbox_theme': {
        'max_logo_kb': 512,
        'max_font_kb': 2048,
    },
}
```

| Key | Type | Default | Description |
| --- | --- | --- | --- |
| `max_logo_kb` | int | `512` | Largest logo or favicon file accepted, in kilobytes (uploads and imports). |
| `max_font_kb` | int | `2048` | Largest font file accepted, in kilobytes (uploads and imports). |

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
  "favicon": "",
  "logo_height": 32,
  "logo_margin_top": 12,
  "logo_margin_bottom": 12,
  "edition": "netbox",
  "edition_text": "",
  "custom_colors": [{"slug": "brand", "name": "Brand", "light": "#0b63c5", "dark": "#5aa9ff"}],
  "status_colors": {"active": "nbt-brand", "planned": "purple"},
  "typography": {"body_family": "font:Acme Sans", "headings_family": "", "mono_family": "system-mono",
                 "base_size": 14, "line_height": 1.43, "body_weight": 400, "bold_weight": 600,
                 "headings_weight": 600, "letter_spacing": 0, "headings_letter_spacing": 0,
                 "headings_case": "none", "tabular_numbers": false},
  "fonts": [{"family": "Acme Sans", "weight": 400, "style": "normal", "variable": false,
             "filename": "AcmeSans-Regular.woff2", "data": "<base64>"}]
}
```

*Import* replaces the saved theme. Colors must be `#rrggbb`; unknown names
are ignored. Missing ones follow the color they were split from in older
versions (top bar and table header from card background, button and change
action colors from the status colors, and so on), else
get NetBox's color. Logos and the favicon are checked like
uploads; one the file leaves out or empty keeps the saved one. `edition` is `netbox`, `hidden` or `custom`. Widget colors keep
their `slug` (dashboard widgets store `nbt-<slug>`); a missing slug is made
from the name. `status_colors` maps a status value to one of NetBox's color
names or `nbt-<slug>`; statuses this NetBox does not have are skipped. Font sources in
`typography` are `""` (NetBox's; for headings the body font), `uploaded`,
`system`, `serif` (body, headings) or `system-mono` (code). Font slots:
`body` `regular` / `medium` / `bold` / `italic`, `headings` `bold`, `mono`
`regular`. A file without a `fonts` list keeps the
saved font files; with one, it replaces them. The
color names are listed in `netbox_theme/colors.py` (`GROUPS`).
