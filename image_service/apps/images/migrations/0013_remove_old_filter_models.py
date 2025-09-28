# Generated manually to remove old filter models

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('images', '0012_add_indexes'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Filter',
        ),
        migrations.DeleteModel(
            name='FilterOption',
        ),
    ]