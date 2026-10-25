from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_theme', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='theme',
            name='typography',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name='FontFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('role', models.CharField(max_length=10)),
                ('slot', models.CharField(max_length=10)),
                ('detected', models.CharField(blank=True, max_length=100)),
                ('variable', models.BooleanField(default=False)),
                ('format', models.CharField(max_length=10)),
                ('filename', models.CharField(blank=True, max_length=200)),
                ('data', models.BinaryField()),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'font file',
                'verbose_name_plural': 'font files',
                'ordering': ('role', 'slot'),
                'constraints': [
                    models.UniqueConstraint(fields=('role', 'slot'), name='netbox_theme_fontfile_role_slot'),
                ],
            },
        ),
    ]
