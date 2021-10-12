from uuid import uuid4

from django.db import models

from users.models.user import User


class Friend(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    user_from = models.ForeignKey(User, related_name="friends_from", db_index=True, on_delete=models.CASCADE)
    user_to = models.ForeignKey(User, related_name="friends_to", on_delete=models.CASCADE)

    is_subscribed_to_posts = models.BooleanField(default=True)
    is_subscribed_to_comments = models.BooleanField(default=True)

    class Meta:
        db_table = "friends"
        unique_together = [["user_from", "user_to"]]

    @classmethod
    def add_friend(cls, user_from, user_to):
        return cls.objects.get_or_create(
            user_from=user_from,
            user_to=user_to,
        )

    @classmethod
    def delete_friend(cls, user_from, user_to):
        return cls.objects.filter(
            user_from=user_from,
            user_to=user_to,
        ).delete()

    @classmethod
    def friends_for_user(cls, user_to):
        return cls.objects.filter(user_to=user_to).select_related("user_from")

    @classmethod
    def user_friends(cls, user_from):
        return cls.objects.filter(user_from=user_from).select_related("user_to")
