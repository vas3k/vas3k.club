from datetime import datetime
from uuid import uuid4

from django.db import models

from rooms.models import Room
from users.models.user import User


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    json_text = models.JSONField()
    channel_msg_id = models.CharField(max_length=32, null=True, blank=True, unique=True)
    discussion_msg_id = models.CharField(max_length=32, null=True, blank=True)
    room = models.ForeignKey(Room, null=True, on_delete=models.SET_NULL)
    room_chat_msg_id = models.CharField(max_length=32, null=True, blank=True)

    class Meta:
        db_table = "questions"


class HelpDeskUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    banned_until = models.DateTimeField(null=True)
    ban_reason = models.CharField(max_length=512, null=True)

    class Meta:
        db_table = "help_desk_users"

    @property
    def is_banned(self) -> bool:
        return self.banned_until and self.banned_until > datetime.utcnow()
