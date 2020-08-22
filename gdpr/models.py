from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.db import models

from club.exceptions import RateLimitException
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

    @classmethod
    def register_archive_request(cls, user):
        latest_request = DataRequests.objects\
            .filter(user=user, type=DataRequests.TYPE_ARCHIVE)\
            .order_by("-created_at")\
            .first()

        if latest_request and latest_request.created_at > datetime.utcnow() - settings.GDPR_ARCHIVE_REQUEST_TIMEDELTA:
            raise RateLimitException(
                title="Вы уже запрашивали архив совсем недавно",
                message="Генерация архива — сложная задача, "
                        "потому нам приходится ограничивать количество запросов в день. "
                        "Приходите завтра!"
            )

        return DataRequests.objects.create(
            user=user,
            type=DataRequests.TYPE_ARCHIVE,
        )

    @classmethod
    def register_forget_request(cls, user):
        return DataRequests.objects.create(
            user=user,
            type=DataRequests.TYPE_FORGET,
        )
