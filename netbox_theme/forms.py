from django import forms
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from . import colors, custom_colors, fonts, logos, statuses, transfer
from .models import FONTS_CACHE_KEY, EditionChoices, FontFile, Theme

__all__ = ('ThemeForm', 'ThemeImportForm')


def field_name(mode, token):
    return f'{mode}_{token}'


class ThemeForm(forms.Form):
    """
    The editor: a name, one color input per token and mode
    (`light_primary`, `dark_primary`, ...), a logo per mode with its size,
    the edition label, custom colors (rows of `custom_color_slug`, `_name`,
    `_light`, `_dark` inputs), status colors (`status_color_<value>`
    selects), font files (`font_<role>_<slot>` uploads and `_remove`
    checkboxes) and typography (`typography_<setting>`). Everything after the edition label is read in
    clean().
    """
    name = forms.CharField(label=_('Name'), max_length=100)
    logo_light = forms.FileField(label=_('Sidebar, light mode'), required=False)
    logo_dark = forms.FileField(
        label=_('Sidebar, dark mode'), required=False,
        help_text=_('Leave empty to use the light mode logo in dark mode too.'),
    )
    logo_login_light = forms.FileField(
        label=_('Login page, light mode'), required=False, help_text=_("Leave empty for NetBox's logo."),
    )
    logo_login_dark = forms.FileField(
        label=_('Login page, dark mode'), required=False,
        help_text=_('Leave empty to use the light mode logo in dark mode too.'),
    )
    edition = forms.ChoiceField(label=_('Edition label'), choices=EditionChoices.choices,
                                help_text=_('The "Community" text under the logo and on the login page.'))
    edition_text = forms.CharField(label=_('Text'), max_length=50, required=False)
    logo_height = forms.IntegerField(label=_('Height'), min_value=16, max_value=120)
    logo_margin_top = forms.IntegerField(label=_('Space above'), min_value=0, max_value=80)
    logo_margin_bottom = forms.IntegerField(label=_('Space below'), min_value=0, max_value=80)
    clear_logo_light = forms.BooleanField(label=_('Remove'), required=False)
    clear_logo_dark = forms.BooleanField(label=_('Remove'), required=False)
    clear_logo_login_light = forms.BooleanField(label=_('Remove'), required=False)
    clear_logo_login_dark = forms.BooleanField(label=_('Remove'), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fonts_put_in_use = []
        hex_color = RegexValidator(colors.HEX, _('Enter a color as #rrggbb.'))
        for mode in colors.MODES:
            for _group, _label, tokens in colors.GROUPS:
                for token, label in tokens:
                    self.fields[field_name(mode, token)] = forms.CharField(
                        label=label, max_length=7, validators=[hex_color],
                        widget=forms.TextInput(attrs={
                            'type': 'color', 'class': 'form-control form-control-color',
                            'data-nbt-token': token, 'data-nbt-mode': mode,
                        }),
                    )

    def clean_logo(self, slot):
        upload = self.cleaned_data.get(f'logo_{slot}')
        return logos.to_data_uri(upload.read()) if upload else None

    def clean_logo_light(self):
        return self.clean_logo('light')

    def clean_logo_dark(self):
        return self.clean_logo('dark')

    def clean_logo_login_light(self):
        return self.clean_logo('login_light')

    def clean_logo_login_dark(self):
        return self.clean_logo('login_dark')

    def clean(self):
        data = super().clean()
        if data.get('edition') == EditionChoices.CUSTOM and not data.get('edition_text', '').strip():
            self.add_error('edition_text', _('Enter the text to show.'))
        try:
            data['custom_colors'] = custom_colors.clean(self.custom_color_rows())
            data['status_colors'] = statuses.clean(
                self.status_color_values(), {entry['slug'] for entry in data['custom_colors']},
            )
            data['font_uploads'], data['font_removals'] = self.clean_fonts()
            data['typography'] = fonts.clean_typography(self.with_new_fonts_in_use(data))
        except ValidationError as error:
            self.add_error(None, error)
        return data

    def clean_fonts(self):
        """
        ({(role, slot): (info, bytes, filename)} to store, {(role, slot), ...}
        to remove). Uploads come from `font_<role>_<slot>` inputs.
        """
        uploads, removals = {}, set()
        for role, slot in sorted(fonts.ALL_SLOTS):
            upload = self.files.get(f'font_{role}_{slot}') if self.files else None
            if upload:
                raw = upload.read()
                uploads[(role, slot)] = (fonts.read(raw, upload.name), raw, upload.name)
            elif self.data.get(f'font_{role}_{slot}_remove'):
                removals.add((role, slot))
        return uploads, removals

    def with_new_fonts_in_use(self, data):
        """
        The typography settings, where a role that gets its first upload and
        still has NetBox's font switches to it: anyone who uploads a font
        expects to see it. `self.fonts_put_in_use` names those roles.
        """
        values = dict(self.typography_values())
        self.fonts_put_in_use = []
        for role in sorted({role for role, _slot in data['font_uploads']}):
            if not values.get(f'{role}_family'):
                values[f'{role}_family'] = 'uploaded'
                self.fonts_put_in_use.append(dict(fonts.ROLES)[role])
        return values

    def typography_values(self):
        """Typography settings as submitted (or initial)."""
        if not self.is_bound:
            return self.initial.get('typography', {})
        values = {key: self.data.get(f'typography_{key}') for key in fonts.SETTINGS}
        return {key: value for key, value in values.items() if value is not None or key == 'tabular_numbers'}

    def save_fonts(self):
        """Store uploads in their slots and empty the slots marked Remove."""
        data = self.cleaned_data
        for role, slot in data['font_removals']:
            FontFile.objects.filter(role=role, slot=slot).delete()
        for (role, slot), (info, raw, filename) in data['font_uploads'].items():
            FontFile.put(role, slot, info, raw, filename)
        cache.delete(FONTS_CACHE_KEY)

    def status_color_values(self):
        """{status value: color} as submitted (or initial); '' is NetBox's."""
        if not self.is_bound:
            return self.initial.get('status_colors', {})
        return {value: self.data.get(f'status_color_{value}', '') for value, _label in statuses.statuses()}

    def custom_color_rows(self):
        """Widget color rows as submitted (or initial), for clean() and the template."""
        if not self.is_bound:
            return self.initial.get('custom_colors', [])
        columns = [self.data.getlist(f'custom_color_{key}') for key in ('slug', 'name', 'light', 'dark')]
        return [
            {'slug': slug, 'name': name, 'light': light, 'dark': dark}
            for slug, name, light, dark in zip(*columns)
        ]

    def groups(self, mode):
        """[(group, label, [bound field, ...]), ...] for the template."""
        return [
            (group, label, [self[field_name(mode, token)] for token, _label in tokens])
            for group, label, tokens in colors.GROUPS
        ]

    def apply(self, theme):
        """Copy the cleaned values onto `theme` (not saved)."""
        data = self.cleaned_data
        theme.name = data['name']
        theme.edition = data['edition']
        theme.edition_text = data['edition_text'].strip()
        theme.logo_height = data['logo_height']
        theme.logo_margin_top = data['logo_margin_top']
        theme.logo_margin_bottom = data['logo_margin_bottom']
        theme.custom_colors = data['custom_colors']
        theme.status_colors = data['status_colors']
        theme.typography = data['typography']
        for mode in colors.MODES:
            setattr(theme, mode, {token: data[field_name(mode, token)].lower() for token in colors.TOKENS})
        for slot in logos.SLOTS:
            if data[f'logo_{slot}']:
                setattr(theme, f'logo_{slot}', data[f'logo_{slot}'])
            elif data[f'clear_logo_{slot}']:
                setattr(theme, f'logo_{slot}', '')
        return theme

    @classmethod
    def initial_for(cls, theme):
        initial = {
            'name': theme.name if theme else 'Custom',
            'edition': theme.edition if theme else EditionChoices.NETBOX,
            'edition_text': theme.edition_text if theme else '',
            'custom_colors': custom_colors.stored(theme),
            'status_colors': statuses.stored(theme),
            'typography': fonts.with_defaults(theme.typography if theme else {}),
        }
        defaults = theme or Theme()
        for field in ('logo_height', 'logo_margin_top', 'logo_margin_bottom'):
            initial[field] = getattr(defaults, field)
        for mode in colors.MODES:
            values = theme.colors(mode) if theme else colors.NETBOX[mode]
            initial.update({field_name(mode, token): value for token, value in values.items()})
        return initial


class ThemeImportForm(forms.Form):
    file = forms.FileField(label=_('Theme file'))

    def clean_file(self):
        """The theme's field values (transfer.load), or a form error."""
        return transfer.load(self.cleaned_data['file'].read())
