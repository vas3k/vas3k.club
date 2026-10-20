from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("posts", "0039_post_moderation_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="post",
            name="moderation_message",
        ),
        migrations.AddField(
            model_name="post",
            name="moderation_reason",
            field=models.CharField(max_length=32, null=True, blank=True),
        ),
    ]
