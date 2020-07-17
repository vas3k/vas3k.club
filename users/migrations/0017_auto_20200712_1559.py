# Generated by Django 3.0.4 on 2020-07-12 15:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_auto_20200712_1557'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True),
        ),
        migrations.RunSQL("""
            CREATE OR REPLACE FUNCTION generate_random_hash(int)
            RETURNS text
            AS $$
              SELECT array_to_string(
                ARRAY (
                  SELECT substring(
                    'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#*+./:<=>?@[]()^_~'
                    FROM (random() * 72)::int FOR 1)
                  FROM generate_series(1, $1) ), '' )
            $$ LANGUAGE sql;
        """),
        migrations.RunSQL("""
            update users set secret_hash = generate_random_hash(16);
        """),
        migrations.RunSQL("""
            drop function generate_random_hash(int);
        """),
    ]
