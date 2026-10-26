# netbox-theme

A NetBox plugin that gives NetBox your organization's colors, logos and
fonts, for every user, in light and dark mode. Admins edit the theme in the
web UI with a live preview; nothing needs a restart.

## What it does

- **One theme for everyone.** *Plugins → Theme* edits the colors NetBox is
  drawn with, for light and dark mode separately. Every user sees the saved
  theme; their own light/dark switch keeps working.
- **Presets and per-color pickers.** Start from a preset (NetBox, Ocean,
  Forest, Sunset, Royal, Graphite, Navy sidebar) and adjust any color: brand
  color and the text on it, links, page background, top bar, text, muted
  text, borders, card background and header, table header and its text, form
  fields, sidebar background, text and headings, the status (success, info, warning, danger, secondary) and NetBox's action
  buttons (Clone, Edit, Delete, Import, Export) and the Create / Update /
  Delete badges of the changelog and change requests. Text on status colored
  badges and buttons turns dark or white, whichever reads better.
- **Custom colors.** Add your own named colors (with a light and a dark mode
  value). Dashboard widgets list them under *Theme* in their *Color* choice,
  next to NetBox's Blue, Green and so on, which stay as they are. *Add
  colors from a color pack* reads an Adobe Swatch Exchange file (.ase, as in
  most brand kits) and adds every swatch.
- **Status colors.** Pick the badge color of each status (Active, Planned,
  Offline...), from NetBox's colors or your own. It applies on every object
  type, NetBox's and plugins', in lists and on object pages.
- **Live preview.** The editor page redraws itself as you pick colors, with a
  sample of buttons, badges, an alert and a table. *Light* / *Dark* preview
  either mode without changing your own setting. A chosen logo shows in the
  sidebar before saving.
- **Logo.** Upload an SVG, PNG, JPEG, GIF or WebP for the top of the sidebar,
  one for light mode and optionally another for dark mode, and set its height
  and the space above and below it (even by default). The login page has its
  own logo upload; without one it keeps NetBox's.
- **Favicon.** Upload the browser tab icon (ICO, SVG, PNG, JPEG, GIF or
  WebP); without one NetBox's is shown.
- **Fonts.** For body text, headings and code, choose NetBox's font, a
  system font or upload your own (WOFF2, WOFF, TTF or OTF). Body text has
  slots for the styles NetBox uses: Regular (enough on its own), Medium,
  Bold and Italic; headings and code take one file. An uploaded font is used
  as soon as you save, and an *In use* line says what each part shows.
  Other fonts are scaled so their letters are as tall as NetBox's, so menus,
  tables and headings keep their proportions (*Keep NetBox's text size*).
  *Advanced* has text size, line height, heading weight, letter spacing,
  heading case and tabular numbers (digits that line up in columns).
- **Edition label.** Keep, hide or replace the "Community" text under the
  logo (sidebar and login page).
- **Reset** in each section puts just that section back to NetBox's
  defaults (saved with *Save*).
- **Restore NetBox defaults** deletes the saved theme; NetBox then looks
  exactly as shipped.
- **Export / Load theme file**: the theme (colors, logos and favicon) as one JSON file, to back
  it up or copy it to another NetBox.

## What it does not do

- The favicon and the page title stay NetBox's.
- The release line at the bottom of the sidebar stays NetBox's.
- The gray scale Tabler uses for a few details (icons, disabled controls)
  is left as is; page, card, text and border colors cover the rest.
- Per-user themes: the theme is global.

## Requirements

- NetBox **4.7** or later. Tested with NetBox 4.7.0 and 4.7.3.
- No other NetBox plugins.

## Installation

```bash
pip install git+https://github.com/mattivaisanen/netbox-theme.git
```

Add it to `configuration.py` and run the migrations:

```python
PLUGINS = ['netbox_theme']
```

```bash
python manage.py migrate
```

Settings and permissions: [docs/configuration.md](docs/configuration.md).
How it works inside: [DEVELOPER.md](DEVELOPER.md).

### Upgrading

```bash
pip install --upgrade git+https://github.com/mattivaisanen/netbox-theme.git
python manage.py migrate
```

Then restart NetBox. Check [CHANGELOG.md](CHANGELOG.md) for anything a
release asks you to do.

## License

Apache License 2.0, see [LICENSE](LICENSE).
