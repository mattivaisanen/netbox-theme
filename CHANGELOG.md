# Changelog

## 0.2.0 (2026-11-01)

New:

- Site title: replace "NetBox" at the end of browser tab titles with your
  own name (*Logo and label → Browser tab*).
- Login message: plain text shown under the logo on the login page, such
  as a usage notice.
- Favicon: upload your own browser tab icon (ICO, SVG, PNG, JPEG, GIF or
  WebP) under *Logo and label*. It shows on every page and the login page,
  travels in theme files and goes back to NetBox's with *Reset* or *Restore
  NetBox defaults*.
- Button colors: Clone, Edit, Delete, Import (also Bookmark and Subscribe)
  and Export buttons, and custom links in the same colors, follow the theme
  instead of NetBox's fixed green, yellow, red, cyan and purple, with dark or
  white text, whichever reads better. A theme saved earlier gives them its
  success, warning, danger and info colors.
- Change action colors: the Create, Update and Delete badges in the
  changelog (and in netbox-change-approval's change requests) follow the
  theme instead of NetBox's fixed green, blue and red. A theme saved earlier
  gives Create and Delete its success and danger colors.

Changed:

- Only superusers can open the theme editor, save, import, export or
  restore defaults. The `change_theme` permission no longer grants it.

Fixed:

- Logos, favicons, fonts and theme files that are too large are turned away
  before they are read, instead of being loaded into memory first.
- Font files are served with the same locked-down security headers as logos.
- Focused form fields and search boxes had NetBox's teal border, and link
  buttons turned teal on hover, whatever the theme. Both follow the theme's
  primary and link colors now.

## 0.1.0 (2026-10-26)

First release.

New:

- Theme editor (*Plugins → Theme*, for users with `change_theme`): one
  theme for every user, set separately for light and dark mode, with
  presets, a color picker per color and a live preview. *Reset* in each
  section puts just that section back to NetBox's defaults.
- Colors for brand, links, page, top bar, cards, card headers, table
  headers, form fields, sidebar and status (secondary, success, info,
  warning, danger). Text and icons on colored buttons, badges and widget
  headers are dark or white, whichever reads better.
- Custom colors with a light and a dark value, offered in every dashboard
  widget's color choice; *Add colors from a color pack* reads an Adobe
  Swatch Exchange (.ase) file.
- Status colors: one badge color per status (Active, Planned...) on every
  object type, NetBox's or plugins', from NetBox's colors or your own.
- Logos for the sidebar and the login page, per mode, with height and
  spacing (even above and below by default); centered on narrow screens.
- Edition label under the logo: NetBox's, hidden or custom text.
- Fonts for body text (Regular, Medium, Bold, Italic), headings and code:
  NetBox's, a system font or uploaded WOFF2, WOFF, TTF or OTF files, scaled
  to NetBox's letter height. Advanced: text size, line height, heading
  weight, letter spacing, heading case, tabular numbers.
- Rack elevations follow the theme's colors.
- *Restore NetBox defaults*, *Export* and *Load theme file* (JSON with
  colors, logos, fonts and settings; logos and fonts a file leaves out
  stay).
