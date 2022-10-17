from uuid import uuid4

from django.db import models

from posts.models.post import Post
from users.models.user import User


class PostSubscription(models.Model):
    TYPE_ALL_COMMENTS = "all"
    TYPE_TOP_LEVEL_ONLY = "top"
    TYPES = [
        (TYPE_ALL_COMMENTS, "Все комментарии"),
        (TYPE_TOP_LEVEL_ONLY, "Только комментарии первого уровня"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="subscriptions", db_index=True, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="subscriptions", db_index=True, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=32, choices=TYPES, default=TYPE_TOP_LEVEL_ONLY)

    class Meta:
        db_table = "post_subscriptions"

    @classmethod
    def get(cls, user, post):
        return cls.objects.filter(user=user, post=post).first()

    @classmethod
    def subscribe(cls, user, post, type=TYPE_TOP_LEVEL_ONLY):
        return cls.objects.update_or_create(user=user, post=post, defaults=dict(type=type))

    @classmethod
    def unsubscribe(cls, user, post):
        return cls.objects.filter(user=user, post=post).delete()

    @classmethod
    def post_subscribers(cls, post):
        return cls.objects.filter(post=post).select_related("user")
