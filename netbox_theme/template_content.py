import logging

from django.urls import reverse
from django.utils.safestring import mark_safe

from netbox.plugins import PluginTemplateExtension

from . import colors, css, custom_colors, logos
from .models import Theme

logger = logging.getLogger('netbox_theme')


class ThemeHead(PluginTemplateExtension):
    """
    The saved theme's CSS on every page (models=None: head() is only offered
    for every page). Nothing at all without a saved theme, so NetBox then
    looks exactly as shipped.
    """
    def head(self):
        try:
            if self.on_editor():
                return ''  # The editor draws the colors being edited instead.
            theme = Theme.current()
            if theme is None:
                return ''
            return self.render('netbox_theme/inc/head.html', extra_context={
                # Values are validated #rrggbb colors (colors.complete), safe in CSS.
                'light_variables': mark_safe(colors.css_variables(theme.colors('light'))),
                'dark_variables': mark_safe(colors.css_variables(theme.colors('dark'))),
                **self.logo_urls(theme),
                'edition_css': css.edition(theme.edition, theme.edition_text),
                'logo_size_css': css.logo_size(theme.logo_height, theme.logo_margin_top, theme.logo_margin_bottom),
                'custom_color_css': mark_safe(custom_colors.css(custom_colors.stored(theme))),
            })
        except Exception:
            # A page never breaks over colors.
            logger.exception('netbox_theme: could not draw the theme')
            return ''

    def on_editor(self):
        match = getattr(self.context.get('request'), 'resolver_match', None)
        return bool(match) and match.view_name == 'plugins:netbox_theme:theme'

    @staticmethod
    def logo_url(theme, slot):
        if not theme.logo(slot):
            return ''
        return f"{reverse('plugins:netbox_theme:logo', args=[slot])}?v={theme.version}"

    @classmethod
    def logo_urls(cls, theme):
        """{'logo_<slot>': url or ''} for inc/head.html."""
        return {f'logo_{slot}': cls.logo_url(theme, slot) if theme else '' for slot in logos.SLOTS}


template_extensions = [ThemeHead]
