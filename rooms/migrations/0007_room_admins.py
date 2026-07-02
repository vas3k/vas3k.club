import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rooms', '0006_alter_room_icon'),
    ]

    operations = [
        migrations.AddField(
            model_name='room',
            name='admins',
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=32),
                db_index=True,
                default=list,
                size=None,
            ),
        ),
    ]
