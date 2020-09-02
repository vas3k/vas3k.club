from datetime import datetime, timedelta

from django.db import models


class Topic(models.Model):
    slug = models.CharField(primary_key=True, max_length=32, unique=True)

    name = models.CharField(max_length=64, null=False)
    icon = models.URLField(null=True)
    description = models.TextField(null=True)
    color = models.CharField(max_length=16, null=False)
    style = models.CharField(max_length=256, default="", null=True)

    chat_name = models.CharField(max_length=128, null=True)
    chat_url = models.URLField(null=True)
    chat_id = models.CharField(max_length=64, null=True)

    last_activity_at = models.DateTimeField(auto_now_add=True, null=False)

    is_visible = models.BooleanField(default=True)
    is_visible_on_main_page = models.BooleanField(default=True)

    class Meta:
        db_table = "topics"
        ordering = ["-last_activity_at"]

    def __str__(self):
        return self.name

    def update_last_activity(self):
        now = datetime.utcnow()
        if self.last_activity_at < now - timedelta(minutes=5):
            return Topic.objects.filter(slug=self.slug).update(last_activity_at=now)
