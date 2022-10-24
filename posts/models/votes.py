from datetime import datetime
from uuid import uuid4

from django.conf import settings
from django.db import models

from common.request import parse_ip_address
from posts.models.post import Post
from users.models.user import User


class PostVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="post_votes", db_index=True, null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="voters", db_index=True, on_delete=models.CASCADE)

    ipaddress = models.GenericIPAddressField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "post_votes"
        unique_together = [["user", "post"]]

    @classmethod
    def upvote(cls, user, post, request=None):
        if not user.is_god and (user.id == post.author_id or user.slug in post.coauthors):
            return None, False

        post_vote, is_vote_created = PostVote.objects.get_or_create(
            user=user,
            post=post,
            defaults=dict(
                ipaddress=parse_ip_address(request) if request else None,
            )
        )

        if is_vote_created:
            post.increment_vote_count()
            post.author.increment_vote_count()

        return post_vote, is_vote_created

    @property
    def is_retractable(self):
        return self.created_at >= datetime.utcnow() - settings.RETRACT_VOTE_TIMEDELTA

    @classmethod
    def retract_vote(cls, request, user, post):
        if not user.is_god and (user.id == post.author_id or user.slug in post.coauthors):
            return False

        try:
            post_vote = PostVote.objects.get(
                user=user,
                post=post
            )

            if not post_vote.is_retractable:
                return False

            is_vote_deleted, _ = post_vote.delete()
            if is_vote_deleted:
                post.decrement_vote_count()
                post.author.decrement_vote_count()

                return True if is_vote_deleted > 0 else False
        except PostVote.DoesNotExist:
            return False
