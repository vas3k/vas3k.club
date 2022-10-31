from datetime import datetime
from uuid import uuid4

from django.db import models


class ProTip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    title = models.TextField(null=False)
    text = models.TextField(null=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "pro_tips"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    @classmethod
    def weekly_tip(cls, seed: int):
        tips = cls.objects.filter(is_visible=True)
        number = seed % tips.count()
        return tips[number]
