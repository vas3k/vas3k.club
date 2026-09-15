from django.db import migrations


class Migration(migrations.Migration):
    """Hands the "geo" table over to the map app.

    State-only counterpart of map.0002_move_geo_from_users: the table is kept
    as is, only its owning app changes.
    """

    dependencies = [
        ('users', '0035_user_referer'),
        ('map', '0002_move_geo_from_users'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.DeleteModel(name='Geo'),
            ],
        ),
    ]
