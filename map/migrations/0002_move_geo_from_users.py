from django.db import migrations, models


class Migration(migrations.Migration):
    """Takes ownership of the existing "geo" table from the users app.

    The table itself is untouched: only Django's migration state changes, so this
    must stay paired with users.0036_move_geo_to_map which drops it from the
    users state.
    """

    dependencies = [
        ('map', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name='Geo',
                    fields=[
                        ('id', models.AutoField(primary_key=True, serialize=False)),
                        ('country_en', models.CharField(max_length=256)),
                        ('region_en', models.CharField(max_length=256)),
                        ('city_en', models.CharField(db_index=True, max_length=256)),
                        ('country', models.CharField(max_length=256)),
                        ('region', models.CharField(max_length=256)),
                        ('city', models.CharField(db_index=True, max_length=256)),
                        ('latitude', models.FloatField(default=0.0)),
                        ('longitude', models.FloatField(default=0.0)),
                        ('population', models.IntegerField(default=0)),
                    ],
                    options={
                        'db_table': 'geo',
                        'ordering': ['id'],
                    },
                ),
            ],
        ),
    ]
