from uuid import uuid4

from django.db import models

from users.models.user import User


class UserBadge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User, related_name="achievements", db_index=True, on_delete=models.CASCADE
    )

    type = models.CharField(max_length=32, null=False)
    name = models.CharField(max_length=64, null=False)
    description = models.CharField(max_length=256, null=True)
    image = models.URLField(null=False)
    style = models.CharField(max_length=256, default="", null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_achievements"
        unique_together = [["type", "user"]]
