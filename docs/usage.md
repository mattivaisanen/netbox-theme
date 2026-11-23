# Usage

Everything is done on one page, **Plugins → Theme**, open to superusers
only. Changes show on that page right away; everyone else sees them after
*Save*.

## Make a theme

1. *Choose a preset* as a starting point, or keep NetBox's colors.
2. Adjust any color under **Light mode** and **Dark mode**. The *Sample*
   card and the page itself redraw as you pick; *Light* / *Dark* at the top
   preview either mode without changing your own setting.
3. Under **Logo and label**, upload a sidebar logo (and optionally a separate
   dark mode one), a login page logo, a favicon, and set the site title,
   login message and edition label.
4. Under **Fonts**, pick NetBox's font, a system font or an upload for body
   text, headings and code. Regular alone is enough for body text.
5. *Save*.

## Brand colors and statuses

- **Custom colors** adds named colors with a light and a dark value. Use
  *Add colors from a color pack (.ase)* to import a brand kit's swatches.
- Dashboard widgets then offer them under *Theme* in their *Color* field.
- **Status colors** sets the badge color of each status value (Active,
  Planned...) for every object type at once, from NetBox's colors or your
  custom ones. *NetBox's* keeps the original color per type.

## Undo

- *Reset* in a section puts just that section back to NetBox's defaults
  (applied on *Save*).
- *Restore NetBox defaults* deletes the saved theme at once.

## Move a theme between NetBox instances

*Export* downloads the whole theme (colors, logos, favicon and fonts) as one
JSON file; *Load theme file* on another NetBox replaces its theme with it.
The file format is described in [configuration.md](configuration.md#theme-files).
