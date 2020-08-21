from uuid import uuid4

from django.db import models

from users.models.user import User


class DataRequests(models.Model):
    TYPE_ARCHIVE = "archive"
    TYPE_FORGET = "forget"
    TYPES = [
        (TYPE_ARCHIVE, TYPE_ARCHIVE),
        (TYPE_FORGET, TYPE_FORGET),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="data_requests", on_delete=models.CASCADE)
    type = models.CharField(max_length=32, choices=TYPES, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_requests"
