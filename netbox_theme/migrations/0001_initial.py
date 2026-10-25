import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Theme',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(default='Custom', max_length=100)),
                ('light', models.JSONField(default=dict)),
                ('dark', models.JSONField(default=dict)),
                ('logo_light', models.TextField(blank=True)),
                ('logo_dark', models.TextField(blank=True)),
                ('logo_login_light', models.TextField(blank=True)),
                ('logo_login_dark', models.TextField(blank=True)),
                ('logo_height', models.PositiveSmallIntegerField(
                    default=32,
                    validators=[
                        django.core.validators.MinValueValidator(16),
                        django.core.validators.MaxValueValidator(120),
                    ],
                )),
                ('logo_margin_top', models.PositiveSmallIntegerField(
                    default=12, validators=[django.core.validators.MaxValueValidator(80)],
                )),
                ('logo_margin_bottom', models.PositiveSmallIntegerField(
                    default=12, validators=[django.core.validators.MaxValueValidator(80)],
                )),
                ('edition', models.CharField(default='netbox', max_length=10)),
                ('edition_text', models.CharField(blank=True, max_length=50)),
                ('custom_colors', models.JSONField(blank=True, default=list)),
                ('status_colors', models.JSONField(blank=True, default=dict)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'theme',
                'verbose_name_plural': 'themes',
            },
        ),
    ]
