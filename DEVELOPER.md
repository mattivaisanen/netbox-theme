# Developer guide

How the plugin works and why, for anyone changing it.

## Data

`models.Theme` is one row (pk 1): a name, `light` and `dark` (token →
`#rrggbb`) and a logo per mode stored as a `data:` URI. No row means
NetBox's own look; *Restore NetBox defaults* deletes it (`Theme.reset()`).
`Theme.current()` caches the row (or its absence) in NetBox's cache until
it is saved or deleted. It is a plain Django model, not a NetBoxModel: a
setting, with no list, REST API or change approval.

Logos live in the database rather than `MEDIA_ROOT` so every NetBox
container serves them without shared storage and exports carry them.
`logos.sniff()` decides the type from the content, never the file name.
`views.LogoView` serves them with a year-long cache (URLs carry
`?v=<save time>`) and a `sandbox` Content-Security-Policy, so an SVG opened
directly cannot run scripts (in `<img>` it never can).

## Colors

`colors.GROUPS` lists the tokens the editor shows; `colors.NETBOX` holds
NetBox 4.7's own values for them (read from `netbox.css`), and
`colors.PRESETS` the presets. Tokens added later (top bar, card header,
table header and text, form fields) are derived in `colors.complete()` from
the token they used to share (`_DERIVED`) when a saved theme or import lacks
them, so older themes keep their look; presets list only what they change
and go through the same function. Every value is validated as `#rrggbb` before
it reaches CSS (`colors.complete()` on output, `colors.validate()` on
import, a regex on the form).

`template_content.ThemeHead.head()` adds `inc/head.html` to every page's
`<head>` when a theme is saved:

1. `--nbt-<token>`, `--nbt-<token>-rgb` and `--nbt-<token>-on` (dark or
   white text for that color as a background, `colors.readable_text()`),
   for light mode on `:root` and for dark mode on `html[data-bs-theme=dark]`.
2. `inc/theme.css`, which maps those onto NetBox's (Tabler's) variables
   under `html[data-bs-theme]`, so the current mode's values apply. Shades
   (`*-text-emphasis`, `*-bg-subtle`, link hover...) are `color-mix()`es
   with the page background and text, so they suit either mode.
3. The logos, swapped with `content: url(...)`: the sidebar's
   `.navbar-brand-image` and the login page's `img.logo` (`hide-theme-dark`
   is the light mode image, `hide-theme-light` the dark one). Slots are
   `logos.SLOTS`; a dark slot falls back to its light one (`Theme.logo()`).
4. The edition label (`template_content.edition_css()`): hidden with
   `display: none`, or replaced by shrinking NetBox's text to `font-size: 0`
   and adding the custom text with `::after`. The text goes through
   `css_string()`, which escapes everything but letters and digits.

5. Logo height and spacing (`css.logo_size()`).
6. Widget colors (`custom_colors.css()`): `--nbt-w-<slug>` per mode and a
   `.text-bg-nbt-<slug>` rule each.

`head()` never raises: on any error the page is drawn without the theme.

## Custom colors and status colors

`custom_colors.py`: named colors, used by widgets and statuses as
`nbt-<slug>`.

A dashboard widget's color is a name NetBox puts in a class:
`card-header text-bg-{{ widget.color }}`. `custom_colors.install()` (from
`ready()`) replaces the `color` field's choices on
`extras.dashboard.forms.DashboardWidgetForm` (the add form shares the same
field object) with a callable: NetBox's own list plus a *Theme* group of
`nbt-<slug>` values, read from the saved theme each time a form is built or
validated. A widget whose color was deleted keeps `nbt-<slug>` and draws an
uncolored header. Slugs never change after a color is added, so renaming
keeps widgets' colors.

A status badge's color comes from its ChoiceSet's `colors` map
(`get_status_color()` returns `DeviceStatusChoices.colors.get(status)`;
tables and object pages use it). `statuses.install()` (from `ready()`)
replaces the map of every loaded `*StatusChoices` with `ThemedColors`, a dict
whose `get()` and `[]` return the theme's color for that status value
first. The theme's map is read once per request (kept on the request).
Every app's models (and so their choice sets) are imported before any
`ready()` runs, so plugins' statuses are covered whatever their order.

## NetBox internals this depends on

| NetBox internal | Why |
| --- | --- |
| `extras.dashboard.forms.DashboardWidgetForm.base_fields['color']` (a `ChoiceField`) | Widget colors. Missing field: logged, nothing added. |
| `templates/extras/dashboard/widget.html` draws `text-bg-<color>` | Widget colors. |
| `utilities.choices.ChoiceSet.colors` read with `.get()` / `[]` by `get_<field>_color()` | Status colors. |

## NetBox CSS this depends on

Check these on every NetBox upgrade; `colors.NETBOX` should match too.

| NetBox CSS | Why |
| --- | --- |
| Tabler `--tblr-*` color variables on `:root` / `[data-bs-theme=dark]` | Overridden by `inc/theme.css`. |
| Colors `netbox.css` writes directly: `.page` and the active page tab (the page background, `!important`), `html` itself, `.btn-primary` text, `.text-secondary` in dark mode, `.card`, `.table thead th` (background and text), `.card-header` in `.page-body`, `.navbar`/`.page-header`, `.text-bg-primary`, `.page-link.active`, `.footer .text-primary`, `.list-group-item.active`, `.status-primary`, `.toast-primary`, tom-select's `.ts-control > div.active`, `tr[data-virtual]`, `.text-bg-<color>` text (always near-white in NetBox) | Each has a rule in `inc/theme.css`. |
| Sidebar `.navbar-vertical.navbar-expand-lg` background gradient, `.nav-link-title`, `.nav-link-icon`, `.dropdown-item > a`, `.text-secondary` | Sidebar tokens. |
| `templates/base/layout.html` logo `<img class="navbar-brand-image hide-theme-dark|light">`, `login.html` `<img class="logo hide-theme-dark|light">` | Logo swap. |
| `.navbar-vertical.navbar-expand-lg .navbar-brand` padding, `.navbar-brand-image` height | Logo size and spacing. |
| `.netbox-edition` (`base/layout.html`, `login.html`), sidebar `.fs-5` (.75rem) and login (.875rem) sizes | Edition label. |
| `setmode.js` sets `data-bs-theme` on `<html>` | Mode selectors; the editor watches it to re-preview. |

## Editor

`views.ThemeView` with `templates/netbox_theme/theme.html`. The saved
theme's `head()` is skipped there; the page is drawn in the colors being edited (the form's values go through the same
`inc/head.html`). Its script sets `--nbt-*` inline on `<html>` for the
current mode on every change and when the mode switches; preset buttons only
fill the inputs. Nothing is saved until *Save*.

## Tests

`netbox_theme/tests/`, run from a NetBox checkout:

```bash
python manage.py test netbox_theme
```

CI (`.github/workflows/test.yml`) runs on pull requests only, on the oldest
supported NetBox and the latest tested one.
