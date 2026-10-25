"""
Theme: the one color scheme and logo NetBox is drawn with.

A single row (pk 1). No row means NetBox's own look: "Restore NetBox
defaults" deletes it. A plain Django model rather than a NetBoxModel: it is
a setting, not inventory, so it has no list, tags or REST API, and an
approval plugin does not gate it.
"""
from django.core.cache import cache
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from . import colors, logos

__all__ = ('EditionChoices', 'FontFile', 'Theme')

CACHE_KEY = 'netbox_theme:current'
FONTS_CACHE_KEY = 'netbox_theme:fonts'


class EditionChoices(models.TextChoices):
    """What the edition label ("Community") under the logo shows."""
    NETBOX = 'netbox', _("NetBox's")
    HIDDEN = 'hidden', _('Hidden')
    CUSTOM = 'custom', _('Custom text')
_MISSING = object()


class Theme(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=100, default='Custom')
    light = models.JSONField(verbose_name=_('light mode colors'), default=dict)
    dark = models.JSONField(verbose_name=_('dark mode colors'), default=dict)
    # data: URIs (logos.py). A blank dark logo falls back to the light one.
    # The login page has its own; without them it shows NetBox's.
    logo_light = models.TextField(verbose_name=_('logo (light mode)'), blank=True)
    logo_dark = models.TextField(verbose_name=_('logo (dark mode)'), blank=True)
    logo_login_light = models.TextField(verbose_name=_('login page logo (light mode)'), blank=True)
    logo_login_dark = models.TextField(verbose_name=_('login page logo (dark mode)'), blank=True)
    # Sidebar logo size and spacing, in pixels. NetBox's own: 32 high, 12
    # above, 0 below; even spacing reads better, so 12 / 12.
    logo_height = models.PositiveSmallIntegerField(
        verbose_name=_('logo height'), default=32, validators=[MinValueValidator(16), MaxValueValidator(120)],
    )
    logo_margin_top = models.PositiveSmallIntegerField(
        verbose_name=_('space above logo'), default=12, validators=[MaxValueValidator(80)],
    )
    logo_margin_bottom = models.PositiveSmallIntegerField(
        verbose_name=_('space below logo'), default=12, validators=[MaxValueValidator(80)],
    )
    edition = models.CharField(
        verbose_name=_('edition label'), max_length=10, choices=EditionChoices.choices, default=EditionChoices.NETBOX,
    )
    edition_text = models.CharField(verbose_name=_('edition label text'), max_length=50, blank=True)
    # Named colors for widgets and statuses (custom_colors.py).
    custom_colors = models.JSONField(verbose_name=_('custom colors'), default=list, blank=True)
    # {status value: color name or nbt-<slug>} (statuses.py).
    status_colors = models.JSONField(verbose_name=_('status colors'), default=dict, blank=True)
    # Font roles and settings (fonts.SETTINGS); {} is NetBox's own.
    typography = models.JSONField(verbose_name=_('typography'), default=dict, blank=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('theme')
        verbose_name_plural = _('themes')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete(CACHE_KEY)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        cache.delete(CACHE_KEY)
        return result

    @classmethod
    def reset(cls):
        """Back to NetBox's own colors and logo."""
        cls.objects.all().delete()
        cache.delete(CACHE_KEY)
        FontFile.clear()

    @classmethod
    def current(cls):
        """The saved theme or None, cached until it changes."""
        theme = cache.get(CACHE_KEY, _MISSING)
        if theme is _MISSING:
            theme = cls.objects.filter(pk=1).first()
            cache.set(CACHE_KEY, theme, None)
        return theme

    def colors(self, mode):
        """Every color for `mode`; anything missing or invalid is NetBox's."""
        return colors.complete(getattr(self, mode), mode)

    def logo(self, slot):
        """The logo for a slot (logos.SLOTS); a dark slot falls back to its light one."""
        if slot not in logos.SLOTS:
            return ''
        value = getattr(self, f'logo_{slot}')
        if not value and slot.endswith('dark'):
            value = getattr(self, f"logo_{slot.removesuffix('dark')}light")
        return value

    @property
    def version(self):
        """Changes with every save; added to logo URLs so browsers can cache them."""
        return int(self.updated.timestamp()) if self.updated else 0


class FontFile(models.Model):
    """
    One uploaded font file (one weight and style of a family, or a variable
    font with every weight). Stored in the database like logos.
    """
    family = models.CharField(verbose_name=_('family'), max_length=60)
    weight = models.PositiveSmallIntegerField(verbose_name=_('weight'), default=400)
    style = models.CharField(verbose_name=_('style'), max_length=10, default='normal')
    variable = models.BooleanField(verbose_name=_('variable weight'), default=False)
    format = models.CharField(verbose_name=_('format'), max_length=10)
    filename = models.CharField(verbose_name=_('file name'), max_length=200, blank=True)
    data = models.BinaryField()
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('family', 'weight', 'style')
        verbose_name = _('font file')
        verbose_name_plural = _('font files')

    def __str__(self):
        return f'{self.family} {self.weight} {self.style}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(FONTS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        cache.delete(FONTS_CACHE_KEY)
        return result

    @classmethod
    def clear(cls):
        cls.objects.all().delete()
        cache.delete(FONTS_CACHE_KEY)

    @classmethod
    def listed(cls):
        """Every font file without its data, cached until one changes."""
        fonts = cache.get(FONTS_CACHE_KEY)
        if fonts is None:
            fonts = list(cls.objects.defer('data'))
            cache.set(FONTS_CACHE_KEY, fonts, None)
        return fonts

    @classmethod
    def families(cls):
        return sorted({font.family for font in cls.listed()})

    @property
    def version(self):
        return int(self.updated.timestamp()) if self.updated else 0
