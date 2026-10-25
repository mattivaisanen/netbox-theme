import logging

from django.urls import reverse
from django.utils.safestring import mark_safe

from netbox.plugins import PluginTemplateExtension

from . import colors, css, custom_colors, fonts, logos
from .models import FontFile, Theme

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
                **self.font_context(theme.typography),
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

    @staticmethod
    def font_url(font):
        return f"{reverse('plugins:netbox_theme:font', args=[font.pk])}?v={font.version}"

    @classmethod
    def font_context(cls, typography):
        """@font-face rules and `--nbt-*` font variables for inc/head.html."""
        variables = fonts.css_variables(typography or {}, FontFile.uploaded_roles())
        return {
            'font_faces': mark_safe(fonts.font_faces(FontFile.listed(), cls.font_url)),
            'font_variables': mark_safe(' '.join(f'{name}: {value};' for name, value in variables.items())),
        }

    @classmethod
    def logo_urls(cls, theme):
        """{'logo_<slot>': url or ''} for inc/head.html."""
        return {f'logo_{slot}': cls.logo_url(theme, slot) if theme else '' for slot in logos.SLOTS}


template_extensions = [ThemeHead]
