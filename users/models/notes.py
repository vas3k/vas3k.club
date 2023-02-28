from uuid import uuid4

from django.db import models

from users.models.user import User


class UserNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user_to = models.ForeignKey(User, related_name="notes", on_delete=models.CASCADE)
    user_from = models.ForeignKey(User, related_name="left_notes", on_delete=models.CASCADE)

    text = models.TextField(null=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_notes"
        ordering = ["-created_at"]
