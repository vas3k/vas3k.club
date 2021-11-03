from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import F

from common.request import parse_ip_address
from posts.models.post import Post
from users.models.user import User


class PostView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="post_views", db_index=True, null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="viewers", db_index=True, on_delete=models.CASCADE)

    ipaddress = models.GenericIPAddressField(null=True)

    first_view_at = models.DateTimeField(auto_now_add=True)
    registered_view_at = models.DateTimeField(auto_now_add=True)
    last_view_at = models.DateTimeField(auto_now=True)

    unread_comments = models.IntegerField(default=0)

    class Meta:
        db_table = "post_views"
        unique_together = [["user", "post"]]

    @classmethod
    def register_view(cls, request, user, post):
        post_view, is_view_created = PostView.objects.get_or_create(
            user=user,
            post=post,
        )

        # save last view timestamp to highlight comments
        last_view_at = post_view.last_view_at

        # increment view counter for new views or for re-opens after cooldown period
        if is_view_created or post_view.registered_view_at < datetime.utcnow() - settings.POST_VIEW_COOLDOWN_PERIOD:
            post_view.registered_view_at = datetime.utcnow()
            post.increment_view_count()

        # reset counters and store last view
        if not is_view_created:
            post_view.unread_comments = 0
            post_view.last_view_at = datetime.utcnow()

        post_view.save()

        return post_view, last_view_at

    @classmethod
    def register_anonymous_view(cls, request, post):
        is_view_created = False
        post_view = PostView.objects.filter(
            post=post,
            ipaddress=parse_ip_address(request),
        ).first()

        if not post_view:
            post_view = PostView.objects.create(
                post=post,
                ipaddress=parse_ip_address(request),
            )
            is_view_created = True

        # increment view counter for new views or for re-opens after cooldown period
        if is_view_created or post_view.registered_view_at < datetime.utcnow() - settings.POST_VIEW_COOLDOWN_PERIOD:
            post_view.registered_view_at = datetime.utcnow()
            post.increment_view_count()
            post_view.save()

        return post_view

    @classmethod
    def increment_unread_comments(cls, comment):
        PostView.objects.filter(post=comment.post, last_view_at__lt=comment.created_at, user__isnull=False)\
            .update(unread_comments=F("unread_comments") + 1)

    @classmethod
    def decrement_unread_comments(cls, comment):
        PostView.objects.filter(post=comment.post, last_view_at__lt=comment.created_at, user__isnull=False)\
            .update(unread_comments=F("unread_comments") - 1)
