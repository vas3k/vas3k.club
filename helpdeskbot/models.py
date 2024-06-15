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
        db_table = "help_desk_questions"


class Answer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    user_name = models.CharField(max_length=255, null=True)
    question = models.ForeignKey(Question, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    telegram_data = models.JSONField()

    class Meta:
        db_table = "help_desk_answers"

    @classmethod
    def create_from_update(cls, question, update):
        return cls(
            user=User.objects.filter(telegram_id=update.message.from_user.id).first(),
            user_name=update.message.from_user.first_name,
            question=question,
            text=update.message.text,
            telegram_data=update.to_dict()
        ).save()


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
