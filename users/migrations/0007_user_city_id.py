from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0006_user_is_email_unsubscribed'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='city_id',
            field=models.CharField(max_length=20, null=True),
        ),
    ]
