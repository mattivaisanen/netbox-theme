"""
Status colors: the badge color of a status value (Active, Planned...) on
every object type, NetBox's and plugins' alike.

NetBox draws a status badge as `text-bg-<color>`, taking the color from its
ChoiceSet's `colors` map (`DeviceStatusChoices.colors.get('active')`, through
`get_status_color()`). install() wraps the `colors` map of every
`*StatusChoices` so a color the theme sets for that value wins. The theme
keys colors by value, so "Active" looks the same on devices, prefixes and
VLANs; values it does not set keep NetBox's per-type color.

A color is one of NetBox's names (`green`) or a custom color (`nbt-<slug>`).
"""
import logging

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from netbox.context import current_request

logger = logging.getLogger('netbox_theme')

SUFFIX = 'StatusChoices'
# NetBox's own color names, as offered for dashboard widgets.
NETBOX_COLORS = (
    'blue', 'indigo', 'purple', 'pink', 'red', 'orange', 'yellow', 'green', 'teal', 'cyan', 'gray', 'black', 'white',
)
_REQUEST_ATTR = '_netbox_theme_status_colors'


def choice_sets():
    """Every loaded ChoiceSet whose name ends in StatusChoices."""
    from utilities.choices import ChoiceSet

    found, todo = set(), [ChoiceSet]
    while todo:
        for subclass in todo.pop().__subclasses__():
            if subclass not in found:
                found.add(subclass)
                todo.append(subclass)
    return sorted((cs for cs in found if cs.__name__.endswith(SUFFIX)), key=lambda cs: cs.__name__)


def statuses():
    """[(value, label), ...] of every status value, sorted by label."""
    from utilities.choices import unpack_grouped_choices

    labels = {}
    for choice_set in choice_sets():
        for value, label in unpack_grouped_choices(list(choice_set)):
            if isinstance(value, str):
                labels.setdefault(value, str(label))
    return sorted(labels.items(), key=lambda item: item[1].lower())


def netbox_defaults():
    """{status value: NetBox's most used color for it} (for the editor's samples)."""
    from collections import Counter

    counts = {}
    for choice_set in choice_sets():
        for value, color in dict.items(choice_set.colors):
            counts.setdefault(value, Counter())[color] += 1
    return {value: counter.most_common(1)[0][0] for value, counter in counts.items()}


def clean(mapping, custom_slugs):
    """Validated {status value: color}; unset statuses are left out. Raises ValidationError."""
    if not isinstance(mapping, dict):
        raise ValidationError(_('Status colors must be an object.'))
    known = {value for value, _label in statuses()}
    allowed = set(NETBOX_COLORS) | {f'nbt-{slug}' for slug in custom_slugs}
    cleaned = {}
    for value, color in mapping.items():
        if not color:
            continue
        if value not in known:
            continue  # A status from a plugin that is not installed here.
        if color not in allowed:
            raise ValidationError(_('Status {value}: unknown color {color}.').format(value=value, color=color))
        cleaned[value] = color
    return cleaned


def stored(theme):
    """The theme's status colors; colors it no longer has are dropped."""
    if theme is None:
        return {}
    from .custom_colors import stored as stored_custom_colors

    slugs = {entry['slug'] for entry in stored_custom_colors(theme)}
    allowed = set(NETBOX_COLORS) | {f'nbt-{slug}' for slug in slugs}
    mapping = theme.status_colors if isinstance(theme.status_colors, dict) else {}
    return {value: color for value, color in mapping.items() if color in allowed}


def overrides():
    """The saved status colors, read once per request. Never raises."""
    from .models import Theme

    request = current_request.get()
    cached = getattr(request, _REQUEST_ATTR, None) if request is not None else None
    if cached is not None:
        return cached
    try:
        result = stored(Theme.current())
    except Exception:
        logger.exception('netbox_theme: could not read status colors')
        result = {}
    if request is not None:
        setattr(request, _REQUEST_ATTR, result)
    return result


class ThemedColors(dict):
    """A ChoiceSet's `colors` map where the theme's status colors win."""
    def get(self, key, default=None):
        return overrides().get(key) or super().get(key, default)

    def __getitem__(self, key):
        return overrides().get(key) or super().__getitem__(key)


def install():
    for choice_set in choice_sets():
        if not isinstance(choice_set.colors, ThemedColors):
            choice_set.colors = ThemedColors(choice_set.colors)
