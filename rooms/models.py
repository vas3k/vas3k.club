import re
from datetime import datetime, timedelta
from uuid import uuid4

from django.db import models
from django.urls import reverse

from users.models.user import User


class Room(models.Model):
    slug = models.CharField(primary_key=True, max_length=32, unique=True)

    title = models.CharField(max_length=64, null=False)
    subtitle = models.CharField(max_length=256, null=True, blank=True)
    image = models.URLField(null=True, blank=True)
    icon = models.URLField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    color = models.CharField(max_length=16, null=False)
    style = models.CharField(max_length=256, default="", null=True, blank=True)
    url = models.URLField(null=True, blank=True)

    chat_name = models.CharField(max_length=128, null=True, blank=True)
    chat_url = models.URLField(null=True, blank=True)
    chat_id = models.CharField(max_length=32, null=True, blank=True)
    chat_member_count = models.IntegerField(default=0)
    send_new_posts_to_chat = models.BooleanField(default=True)
    send_new_comments_to_chat = models.BooleanField(default=False)

    network_group = models.ForeignKey(
        "misc.NetworkGroup",
        related_name="rooms",
        db_index=True, null=True,
        on_delete=models.SET_NULL
    )
    last_activity_at = models.DateTimeField(auto_now_add=True, null=False)

    is_visible = models.BooleanField(default=True)
    is_open_for_posting = models.BooleanField(default=True)

    index = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "rooms"
        ordering = ["index"]

    def __str__(self):
        return self.title

    def emoji(self):
        return re.sub("<.*?>", "", self.icon) if self.icon else ""

    def update_last_activity(self):
        now = datetime.utcnow()
        if self.last_activity_at < now - timedelta(minutes=5):
            return Room.objects.filter(slug=self.slug).update(last_activity_at=now)

    def get_private_url(self):
        if self.url or self.chat_url:
            return reverse("redirect_to_room_chat", kwargs={"room_slug": self.slug})
        return None


class RoomSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="room_subscriptions", db_index=True, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, related_name="subscriptions", db_index=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "room_subscriptions"

    @classmethod
    def get(cls, user, room):
        return cls.objects.filter(user=user, room=room).first()

    @classmethod
    def subscribe(cls, user, room):
        return cls.objects.update_or_create(user=user, room=room)

    @classmethod
    def unsubscribe(cls, user, room):
        return cls.objects.filter(user=user, room=room).delete()

    @classmethod
    def is_subscribed(cls, user, room):
        return cls.objects.filter(
            user=user,
            room=room,
        ).exists()

    @classmethod
    def room_subscribers(cls, room):
        return cls.objects.filter(room=room).select_related("user")


class RoomMuted(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(User, related_name="muted_room", db_index=True, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, related_name="muted_users", db_index=True, on_delete=models.CASCADE)

    class Meta:
        db_table = "room_muted"
        unique_together = [["user", "room"]]

    @classmethod
    def mute(cls, user, room):
        return cls.objects.get_or_create(
            user=user,
            room=room,
        )

    @classmethod
    def unmute(cls, user, room):
        return cls.objects.filter(
            user=user,
            room=room,
        ).delete()

    @classmethod
    def is_muted(cls, user, room):
        return cls.objects.filter(
            user=user,
            room=room,
        ).exists()

    @classmethod
    def muted_by_user(cls, user):
        return cls.objects.filter(user=user)

