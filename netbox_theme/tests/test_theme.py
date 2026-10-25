"""Colors, logos, theme files and the theme pages."""
import base64
import json

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from .. import colors, logos, transfer, custom_colors
from ..models import Theme

URL = 'plugins:netbox_theme:'
PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
SVG = b'<?xml version="1.0"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'


class ColorTests(SimpleTestCase):
    def test_complete_fills_missing_and_invalid_with_netbox(self):
        result = colors.complete({'primary': '#ABCDEF', 'link': 'red', 'nope': '#000000'}, 'dark')
        self.assertEqual(result['primary'], '#abcdef')
        self.assertEqual(result['link'], colors.NETBOX['dark']['link'])
        self.assertEqual(set(result), set(colors.TOKENS))

    def test_newer_colors_follow_older_ones(self):
        # A theme saved before Top bar / Table header existed keeps its look.
        dark = colors.complete({'surface': '#123456', 'body_bg': '#000000'}, 'dark')
        self.assertEqual((dark['header'], dark['table_header'], dark['input_bg']), ('#123456', '#123456', '#000000'))
        self.assertEqual(colors.complete({}, 'light'), colors.NETBOX['light'])

    def test_validate_rejects_bad_colors(self):
        with self.assertRaises(ValidationError):
            colors.validate({'primary': 'url(x);}'}, 'light')

    def test_css_variables(self):
        css = colors.css_variables(colors.NETBOX['light'])
        self.assertIn('--nbt-primary: #00857d; --nbt-primary-rgb: 0, 133, 125;', css)
        self.assertIn('--nbt-sidebar-text:', css)

    def test_readable_text(self):
        self.assertEqual(colors.readable_text('#ffeb3b'), colors.DARK_TEXT)
        self.assertEqual(colors.readable_text('#1e40af'), colors.LIGHT_TEXT)
        self.assertIn('--nbt-warning-on: #111827;', colors.css_variables(colors.NETBOX['light']))

    def test_presets_are_complete(self):
        for slug, _label, values in colors.PRESETS:
            for mode in colors.MODES:
                self.assertEqual(colors.validate(values[mode], mode), values[mode], slug)


class CustomColorTests(SimpleTestCase):
    def test_clean(self):
        cleaned = custom_colors.clean([{'name': ' Brand Blue ', 'light': '#0B63C5', 'dark': '#5aa9ff'}])
        self.assertEqual(cleaned, [{'slug': 'brand-blue', 'name': 'Brand Blue', 'light': '#0b63c5', 'dark': '#5aa9ff'}])
        # A renamed color keeps its slug, so widgets using it keep it.
        renamed = custom_colors.clean([{'slug': 'brand-blue', 'name': 'Corporate', 'light': '#000000', 'dark': '#ffffff'}])
        self.assertEqual(renamed[0]['slug'], 'brand-blue')

    def test_rejects(self):
        for entries in (
            [{'name': '', 'light': '#000000', 'dark': '#000000'}],
            [{'name': 'x', 'light': 'red', 'dark': '#000000'}],
            [{'name': 'Same', 'light': '#000000', 'dark': '#000000'}] * 2,
            'nope',
        ):
            with self.assertRaises(ValidationError, msg=entries):
                custom_colors.clean(entries)


class LogoTests(SimpleTestCase):
    def test_types_come_from_content(self):
        self.assertEqual(logos.sniff(PNG), 'image/png')
        self.assertEqual(logos.sniff(SVG), 'image/svg+xml')
        self.assertIsNone(logos.sniff(b'<html><script>alert(1)</script></html>'))

    def test_round_trip(self):
        uri = logos.to_data_uri(SVG)
        self.assertEqual(logos.from_data_uri(uri), ('image/svg+xml', SVG))

    def test_too_large(self):
        with self.assertRaises(ValidationError):
            logos.to_data_uri(PNG + b'\x00' * 600 * 1024)

    def test_import_rechecks_content(self):
        disguised = 'data:image/png;base64,' + base64.b64encode(b'<html></html>').decode()
        with self.assertRaises(ValidationError):
            logos.check_data_uri(disguised)


class ThemeFileTests(TestCase):
    def test_round_trip(self):
        theme = Theme(name='Ocean', light={'primary': '#112233'}, logo_light=logos.to_data_uri(PNG),
                      edition='custom', edition_text='Acme', logo_height=48,
                      custom_colors=[{'slug': 'brand', 'name': 'Brand', 'light': '#000000', 'dark': '#ffffff'}],
                      status_colors={'active': 'nbt-brand', 'gone': 'nbt-gone'})
        loaded = transfer.load(json.dumps(transfer.dump(theme)).encode())
        self.assertEqual(loaded['name'], 'Ocean')
        self.assertEqual(loaded['light']['primary'], '#112233')
        self.assertEqual(loaded['dark'], colors.NETBOX['dark'])
        self.assertEqual(loaded['logo_light'], theme.logo_light)
        self.assertEqual((loaded['edition'], loaded['edition_text']), ('custom', 'Acme'))
        self.assertEqual((loaded['logo_height'], loaded['logo_margin_top']), (48, 12))
        self.assertEqual(loaded['custom_colors'][0]['name'], 'Brand')
        self.assertEqual(loaded['status_colors'], {'active': 'nbt-brand'})

    def test_rejects_other_files(self):
        for raw in (b'not json', b'[]', b'{"name": "x"}', b'{"netbox_theme": 1, "light": {"primary": "x"}}'):
            with self.assertRaises(ValidationError, msg=raw):
                transfer.load(raw)


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create(username='admin', is_superuser=True)
        cls.user = User.objects.create(username='user')

    def setUp(self):
        cache.clear()
        self.client.force_login(self.admin)

    def form_data(self, **changes):
        data = {'name': 'Mine', 'edition': 'netbox', 'logo_height': 32, 'logo_margin_top': 12, 'logo_margin_bottom': 12}
        for mode in colors.MODES:
            data.update({f'{mode}_{token}': value for token, value in colors.NETBOX[mode].items()})
        data.update(changes)
        return data

    def test_no_theme_leaves_netbox_alone(self):
        page = self.client.get(reverse('home'))
        self.assertNotContains(page, 'id="netbox-theme"')

    def test_admins_only(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse(URL + 'theme')).status_code, 403)
        self.assertEqual(self.client.post(reverse(URL + 'theme_reset')).status_code, 403)

    def test_save_applies_everywhere(self):
        self.assertEqual(self.client.get(reverse(URL + 'theme')).status_code, 200)
        response = self.client.post(reverse(URL + 'theme'), self.form_data(
            light_primary='#123456', logo_light=SimpleUploadedFile('logo.svg', SVG),
        ))
        self.assertEqual(response.status_code, 302)
        page = self.client.get(reverse('home'))
        self.assertContains(page, '--nbt-primary: #123456; --nbt-primary-rgb: 18, 52, 86;')
        self.assertContains(page, reverse(URL + 'logo', args=['light']))

        self.assertNotContains(page, 'img.logo')  # The login page keeps NetBox's logo.
        # Dark mode falls back to the light logo; scripts in an opened SVG are sandboxed.
        logo = self.client.get(reverse(URL + 'logo', args=['dark']))
        self.assertEqual((logo.status_code, logo['Content-Type']), (200, 'image/svg+xml'))
        self.assertIn('sandbox', logo['Content-Security-Policy'])

    def test_custom_colors_join_netbox_choices(self):
        self.client.post(reverse(URL + 'theme'), self.form_data(
            custom_color_slug=[''], custom_color_name=['Brand'], custom_color_light=['#112233'],
            custom_color_dark=['#ddeeff'],
        ))
        self.assertEqual(Theme.objects.get().custom_colors[0]['slug'], 'brand')
        page = self.client.get(reverse('home'))
        self.assertContains(page, '.text-bg-nbt-brand { background-color: var(--nbt-w-brand) !important;')
        self.assertContains(page, '--nbt-w-brand: #112233;')

        from extras.dashboard.forms import DashboardWidgetAddForm, DashboardWidgetForm

        for form_class in (DashboardWidgetForm, DashboardWidgetAddForm):
            form = form_class()
            self.assertIn('nbt-brand', [value for _group, options in form.fields['color'].choices[-1:]
                                        for value, _label in options])
            self.assertIn('blue', [value for value, _label in form.fields['color'].choices[:-1]])
            self.assertEqual(sum(1 for _value, options in form.fields['color'].choices if isinstance(options, list)), 1)
        self.assertTrue(DashboardWidgetForm({'color': 'nbt-brand'}).is_valid())

    def test_status_colors(self):
        from dcim.choices import DeviceStatusChoices
        from ipam.choices import PrefixStatusChoices

        self.assertEqual(DeviceStatusChoices.colors.get('active'), 'green')
        self.client.post(reverse(URL + 'theme'), self.form_data(
            custom_color_slug=[''], custom_color_name=['Live'], custom_color_light=['#00aa00'],
            custom_color_dark=['#00ff00'], status_color_active='nbt-live', status_color_planned='purple',
        ))
        self.assertEqual(Theme.objects.get().status_colors, {'active': 'nbt-live', 'planned': 'purple'})
        cache.clear()
        # Every type's "active" follows the theme; statuses it does not set keep NetBox's color.
        self.assertEqual(DeviceStatusChoices.colors.get('active'), 'nbt-live')
        self.assertEqual(PrefixStatusChoices.colors.get('active'), 'nbt-live')
        self.assertEqual(DeviceStatusChoices.colors['planned'], 'purple')
        self.assertEqual(DeviceStatusChoices.colors.get('offline'), 'gray')

        response = self.client.post(reverse(URL + 'theme'), self.form_data(status_color_active='nbt-missing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(self.client.get(reverse(URL + 'theme')), 'name="status_color_active"')

    def test_logo_size(self):
        self.client.post(reverse(URL + 'theme'), self.form_data(logo_height=40, logo_margin_bottom=20))
        page = self.client.get(reverse('home'))
        self.assertContains(page, '.navbar-brand-image { height: 40px; }')
        self.assertContains(page, 'padding-top: 12px !important; padding-bottom: 20px !important;')
        response = self.client.post(reverse(URL + 'theme'), self.form_data(logo_height=500))
        self.assertEqual(response.status_code, 200)

    def test_edition_label(self):
        self.client.post(reverse(URL + 'theme'), self.form_data(edition='custom', edition_text='Acme "IPAM" </style>'))
        page = self.client.get(reverse('home'))
        self.assertContains(page, 'content: "Acme\\000020\\000022IPAM\\000022\\000020\\00003c\\00002fstyle\\00003e"')
        self.client.post(reverse(URL + 'theme'), self.form_data(edition='hidden'))
        self.assertContains(self.client.get(reverse('home')), '.netbox-edition { display: none !important; }')
        response = self.client.post(reverse(URL + 'theme'), self.form_data(edition='custom'))
        self.assertContains(response, 'Enter the text to show.')

    def test_login_logo(self):
        self.client.post(reverse(URL + 'theme'), self.form_data(logo_login_light=SimpleUploadedFile('l.png', PNG)))
        self.client.logout()
        page = self.client.get(reverse('login'))
        self.assertContains(page, 'img.logo.hide-theme-dark { content: url("' + reverse(URL + 'logo', args=['login_light']))
        self.assertNotContains(page, '.navbar-brand-image.hide-theme-dark { content')
        self.assertEqual(self.client.get(reverse(URL + 'logo', args=['login_dark']))['Content-Type'], 'image/png')
        self.assertEqual(self.client.get(reverse(URL + 'logo', args=['nope'])).status_code, 404)

    def test_bad_input_is_not_saved(self):
        response = self.client.post(reverse(URL + 'theme'), self.form_data(
            dark_text='white', logo_dark=SimpleUploadedFile('logo.png', b'<script>'),
        ))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Theme.objects.exists())

    def test_restore_defaults(self):
        Theme(light={'primary': '#123456'}).save()
        self.assertContains(self.client.get(reverse('home')), 'id="netbox-theme"')
        self.client.post(reverse(URL + 'theme_reset'))
        self.assertFalse(Theme.objects.exists())
        self.assertNotContains(self.client.get(reverse('home')), 'id="netbox-theme"')

    def test_export_and_import(self):
        Theme(name='Exported', dark={'primary': '#abcdef'}).save()
        exported = self.client.get(reverse(URL + 'theme_export'))
        self.assertIn('attachment', exported['Content-Disposition'])
        Theme.reset()
        upload = SimpleUploadedFile('theme.json', exported.content, content_type='application/json')
        self.client.post(reverse(URL + 'theme_import'), {'file': upload})
        theme = Theme.objects.get()
        self.assertEqual((theme.name, theme.dark['primary']), ('Exported', '#abcdef'))
