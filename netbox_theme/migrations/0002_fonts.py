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
                ('family', models.CharField(max_length=60)),
                ('weight', models.PositiveSmallIntegerField(default=400)),
                ('style', models.CharField(default='normal', max_length=10)),
                ('variable', models.BooleanField(default=False)),
                ('format', models.CharField(max_length=10)),
                ('filename', models.CharField(blank=True, max_length=200)),
                ('data', models.BinaryField()),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'font file',
                'verbose_name_plural': 'font files',
                'ordering': ('family', 'weight', 'style'),
            },
        ),
    ]
