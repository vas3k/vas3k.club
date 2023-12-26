from uuid import uuid4

from django.db import models

from users.models.friends import Friend
from users.models.user import User


class Muted(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    user_from = models.ForeignKey(User, related_name="muted_from", db_index=True, on_delete=models.CASCADE)
    user_to = models.ForeignKey(User, related_name="muted_to", on_delete=models.CASCADE)

    comment = models.TextField(null=True)

    class Meta:
        db_table = "muted"
        unique_together = [["user_from", "user_to"]]

    @classmethod
    def mute(cls, user_from, user_to, comment=None):
        Friend.delete_friend(
            user_from=user_from,
            user_to=user_to,
        )

        return cls.objects.get_or_create(
            user_from=user_from,
            user_to=user_to,
            defaults=dict(
                comment=comment,
            )
        )

    @classmethod
    def unmute(cls, user_from, user_to):
        return cls.objects.filter(
            user_from=user_from,
            user_to=user_to,
        ).delete()

    @classmethod
    def is_muted(cls, user_from, user_to):
        return cls.objects.filter(
            user_from=user_from,
            user_to=user_to,
        ).exists()

    @classmethod
    def muted_by_user(cls, user_from):
        return cls.objects.filter(user_from=user_from).select_related("user_to")

    @classmethod
    def who_muted_user(cls, user_to):
        return cls.objects.filter(user_to=user_to).select_related("user_from")
