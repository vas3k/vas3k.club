from uuid import uuid4

from django.db import models

from users.models.user import User


class Apps(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(max_length=64, unique=True)

    secret_key = models.CharField(max_length=128, unique=True)
    app_key = models.CharField(max_length=256, unique=True)
    redirect_urls = models.TextField()

    class Meta:
        db_table = "apps"


class Session(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="sessions", db_index=True, on_delete=models.CASCADE)
    app = models.ForeignKey(Apps, related_name="sessions", null=True, on_delete=models.CASCADE)

    token = models.CharField(max_length=128, unique=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True)

    class Meta:
        db_table = "sessions"
