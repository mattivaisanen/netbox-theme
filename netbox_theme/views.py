from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _
from django.views import View

from . import colors, css, custom_colors, logos, statuses, transfer
from .forms import ThemeForm, ThemeImportForm, field_name
from .models import Theme
from .template_content import ThemeHead

PERMISSION = 'netbox_theme.change_theme'
HOME = 'plugins:netbox_theme:theme'


class ThemeAdminMixin(PermissionRequiredMixin):
    """Theme pages are for users with `change_theme` (superusers have it)."""
    permission_required = PERMISSION


class ThemeView(ThemeAdminMixin, View):
    """The editor: presets, a color input per token and mode, logos."""
    template_name = 'netbox_theme/theme.html'

    def get(self, request):
        theme = Theme.current()
        return self.render(request, ThemeForm(initial=ThemeForm.initial_for(theme)), theme)

    def post(self, request):
        theme = Theme.current()
        form = ThemeForm(request.POST, request.FILES)
        if not form.is_valid():
            return self.render(request, form, theme)
        form.apply(theme or Theme()).save()
        messages.success(request, _('Theme saved.'))
        return redirect(HOME)

    def render(self, request, form, theme):
        current = {mode: self.form_colors(form, mode) for mode in colors.MODES}
        return render(request, self.template_name, {
            'form': form,
            'theme': theme,
            'columns': [(mode, form.groups(mode)) for mode in colors.MODES],
            'logos': [
                (slot, form[f'logo_{slot}'], form[f'clear_logo_{slot}'],
                 ThemeHead.logo_url(theme, slot) if theme and getattr(theme, f'logo_{slot}') else '')
                for slot in logos.SLOTS
            ],
            'presets': [(slug, label) for slug, label, _colors in colors.PRESETS],
            # For the editor's script.
            'preset_colors': {slug: values for slug, _label, values in colors.PRESETS},
            'import_form': ThemeImportForm(),
            'custom_colors': form.custom_color_rows(),
            'status_colors': ('primary', 'secondary', 'success', 'info', 'warning', 'danger'),
            'status_rows': self.status_rows(form),
            'netbox_colors': statuses.NETBOX_COLORS,
            'custom_color_options': self.valid_custom_colors(form),
            'logo_size': [form[f] for f in ('logo_height', 'logo_margin_top', 'logo_margin_bottom')],
            # The page itself is drawn in the colors being edited.
            'light_variables': mark_safe(colors.css_variables(current['light'])),
            'dark_variables': mark_safe(colors.css_variables(current['dark'])),
            **ThemeHead.logo_urls(theme),
            'edition_css': css.edition(form['edition'].value(), form['edition_text'].value() or ''),
            'logo_size_css': self.logo_size_css(form),
            'custom_color_css': mark_safe(custom_colors.css(self.valid_custom_colors(form))),
        })

    @staticmethod
    def logo_size_css(form):
        try:
            return css.logo_size(*(int(form[f].value()) for f in ('logo_height', 'logo_margin_top', 'logo_margin_bottom')))
        except (TypeError, ValueError):
            return ''

    @staticmethod
    def status_rows(form):
        """[(value, label, chosen color or '', NetBox's color), ...] for the template."""
        chosen, defaults = form.status_color_values(), statuses.netbox_defaults()
        return [(value, label, chosen.get(value, ''), defaults.get(value, 'secondary'))
                for value, label in statuses.statuses()]

    @staticmethod
    def valid_custom_colors(form):
        try:
            return custom_colors.clean(form.custom_color_rows())
        except ValidationError:
            return []

    @staticmethod
    def form_colors(form, mode):
        return colors.complete({token: form[field_name(mode, token)].value() for token in colors.TOKENS}, mode)


class ThemeResetView(ThemeAdminMixin, View):
    """Restore NetBox defaults: forget the saved theme and logos."""
    def post(self, request):
        Theme.reset()
        messages.success(request, _('NetBox default colors and logo restored.'))
        return redirect(HOME)


class ThemeExportView(ThemeAdminMixin, View):
    def get(self, request):
        theme = Theme.current() or Theme()
        response = JsonResponse(transfer.dump(theme), json_dumps_params={'indent': 2})
        response['Content-Disposition'] = 'attachment; filename="netbox-theme.json"'
        return response


class ThemeImportView(ThemeAdminMixin, View):
    """Replace the saved theme (colors and logos) with a theme file."""
    def post(self, request):
        form = ThemeImportForm(request.POST, request.FILES)
        if not form.is_valid():
            for errors in form.errors.values():
                for error in errors:
                    messages.error(request, _('Import failed: {error}').format(error=error))
            return redirect(HOME)
        theme = Theme.current() or Theme()
        for field, value in form.cleaned_data['file'].items():
            setattr(theme, field, value)
        theme.save()
        messages.success(request, _('Theme "{name}" imported.').format(name=theme.name))
        return redirect(HOME)


class LogoView(View):
    """
    The saved logo for a slot (logos.SLOTS). Open to everyone who can see NetBox's sidebar.
    Cached for a year: the page asks for it with `?v=<theme version>`.
    """
    def get(self, request, slot):
        theme = Theme.current()
        logo = theme.logo(slot) if theme else ''
        if not logo:
            raise Http404
        try:
            content_type, data = logos.from_data_uri(logo)
        except ValidationError:
            raise Http404
        response = HttpResponse(data, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=31536000, immutable'
        response['X-Content-Type-Options'] = 'nosniff'
        # An SVG opened directly must not run scripts (in <img> it never does).
        response['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
        return response
