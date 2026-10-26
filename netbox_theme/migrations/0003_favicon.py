from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('netbox_theme', '0002_fonts'),
    ]

    operations = [
        migrations.AddField(
            model_name='theme',
            name='favicon',
            field=models.TextField(blank=True),
        ),
    ]
