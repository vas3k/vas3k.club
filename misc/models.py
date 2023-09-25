from datetime import datetime
from uuid import uuid4

from django.db import models
from django.urls import reverse


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


class NetworkGroup(models.Model):
    code = models.CharField(max_length=32, primary_key=True)

    title = models.TextField(null=False)
    text = models.TextField(null=True, blank=True)
    index = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "network_groups"
        ordering = ["index"]

    @classmethod
    def visible_objects(cls):
        return cls.objects.filter(is_visible=True)
