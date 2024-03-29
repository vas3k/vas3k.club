# Generated by Django 3.2.13 on 2023-03-06 16:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authn', '0007_auto_20230305_1518'),
    ]

    operations = [
        migrations.AlterField(
            model_name='oauth2app',
            name='client_id',
            field=models.CharField(blank=True, default='', max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='oauth2authorizationcode',
            name='auth_time',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='oauth2authorizationcode',
            name='client_id',
            field=models.CharField(db_index=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='oauth2token',
            name='client_id',
            field=models.CharField(db_index=True, max_length=32),
        ),
        migrations.AlterField(
            model_name='oauth2token',
            name='issued_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
