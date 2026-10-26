"""
Change action colors: the Create / Update / Delete badges of the changelog
(and of plugins that read the same map, such as change requests).

NetBox colors them from `ObjectChangeActionChoices.colors` (green, blue, red,
through `ObjectChange.get_action_color()`). install() wraps that map so that,
while a theme is saved, it names the theme's classes instead
(`nbta-<action>`, drawn as `text-bg-nbta-<action>` by inc/theme.css). The
`nbta-` prefix cannot clash with custom colors (`nbt-<slug>`). Without a saved
theme the map gives NetBox's colors, so nothing changes.
"""
import logging

from netbox.context import current_request

logger = logging.getLogger('netbox_theme')

PREFIX = 'nbta-'
ACTIONS = ('create', 'update', 'delete')
_REQUEST_ATTR = '_netbox_theme_has_theme'


def themed():
    """Whether a theme is saved, read once per request. Never raises."""
    from .models import Theme

    request = current_request.get()
    cached = getattr(request, _REQUEST_ATTR, None) if request is not None else None
    if cached is not None:
        return cached
    try:
        result = Theme.current() is not None
    except Exception:
        logger.exception('netbox_theme: could not read the theme')
        result = False
    if request is not None:
        setattr(request, _REQUEST_ATTR, result)
    return result


class ThemedActionColors(dict):
    """`ObjectChangeActionChoices.colors`, giving the theme's classes while a theme is saved."""
    def get(self, key, default=None):
        if key in ACTIONS and themed():
            return PREFIX + key
        return super().get(key, default)

    def __getitem__(self, key):
        if key in ACTIONS and themed():
            return PREFIX + key
        return super().__getitem__(key)


def install():
    from core.choices import ObjectChangeActionChoices

    if not isinstance(ObjectChangeActionChoices.colors, ThemedActionColors):
        ObjectChangeActionChoices.colors = ThemedActionColors(ObjectChangeActionChoices.colors)
