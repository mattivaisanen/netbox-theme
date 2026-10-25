"""
Custom colors: named colors the theme adds next to NetBox's own (Blue,
Green...), for dashboard widgets and status badges (statuses.py).

Each is {"slug", "name", "light", "dark"}. A widget or status stores
`nbt-<slug>` as its color; NetBox draws it with the class
`text-bg-nbt-<slug>`, which the theme's CSS colors for the current mode.
Slugs come from the name when a color is added and never change, so renaming
a color keeps it wherever it is used.
"""
import logging

from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .colors import is_color, readable_text

logger = logging.getLogger('netbox_theme')

PREFIX = 'nbt-'
MAX_COLORS = 30


def clean(entries):
    """Validated custom colors. Raises ValidationError."""
    if not isinstance(entries, list):
        raise ValidationError(_('Widget colors must be a list.'))
    if len(entries) > MAX_COLORS:
        raise ValidationError(_('At most {count} custom colors.').format(count=MAX_COLORS))
    cleaned, slugs = [], set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValidationError(_('Each custom color needs a name and two colors.'))
        name = entry.get('name').strip() if isinstance(entry.get('name'), str) else ''
        if not name or len(name) > 50:
            raise ValidationError(_('Each custom color needs a name of up to 50 characters.'))
        if not (is_color(entry.get('light')) and is_color(entry.get('dark'))):
            raise ValidationError(_('{name}: colors must be #rrggbb.').format(name=name))
        slug = slugify(entry.get('slug') or name)[:50]
        if not slug:
            raise ValidationError(_('{name}: the name needs a letter or digit.').format(name=name))
        if slug in slugs:
            raise ValidationError(_('{name}: two custom colors have the same name.').format(name=name))
        slugs.add(slug)
        cleaned.append({'slug': slug, 'name': name, 'light': entry['light'].lower(), 'dark': entry['dark'].lower()})
    return cleaned


def stored(theme):
    """The theme's custom colors; anything invalid in the database is skipped."""
    try:
        return clean(theme.custom_colors) if theme else []
    except ValidationError:
        logger.warning('netbox_theme: ignoring invalid custom colors')
        return []


def css(entries):
    """
    Variables per mode and one rule per color. Slugs are [a-z0-9-] and
    colors validated #rrggbb, so all of it is safe inside <style>.
    """
    def variables(mode):
        return ' '.join(
            f'--nbt-w-{e["slug"]}: {e[mode]}; --nbt-w-{e["slug"]}-on: {readable_text(e[mode])};' for e in entries
        )

    rules = ' '.join(
        f'html[data-bs-theme] .text-bg-{PREFIX}{e["slug"]} {{ background-color: var(--nbt-w-{e["slug"]}) !important;'
        f' color: var(--nbt-w-{e["slug"]}-on) !important; }}'
        for e in entries
    )
    return f':root {{ {variables("light")} }} html[data-bs-theme=dark] {{ {variables("dark")} }} {rules}'


def choices():
    """Custom colors for the widget color choice, as an option group. Never raises."""
    from .models import Theme

    try:
        entries = stored(Theme.current())
    except Exception:
        logger.exception('netbox_theme: could not read custom colors')
        return []
    if not entries:
        return []
    return [(_('Theme'), [(PREFIX + e['slug'], e['name']) for e in entries])]


def install():
    """
    Add the theme's colors to NetBox's widget forms. Their `color` field gets
    callable choices: NetBox's own list, read once, plus the theme's, read
    whenever a form is drawn or validated.
    """
    from extras.dashboard.forms import DashboardWidgetAddForm, DashboardWidgetForm

    for form in (DashboardWidgetForm, DashboardWidgetAddForm):
        field = form.base_fields.get('color')
        if field is None:
            logger.warning('netbox_theme: %s has no color field; custom colors not offered', form.__name__)
            continue
        if getattr(field, '_netbox_theme', False):
            continue  # The add form shares the base form's field object.
        netbox_choices = list(field.choices)
        field.choices = lambda netbox_choices=netbox_choices: netbox_choices + choices()
        field._netbox_theme = True
