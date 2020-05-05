from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import F
from simple_history.models import HistoricalRecords

from club.exceptions import NotFound
from common.request import parse_ip_address, parse_useragent
from posts.models import Post
from users.models import User


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    author = models.ForeignKey(User, related_name="comments", null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)

    reply_to = models.ForeignKey("self", related_name="replies", null=True, on_delete=models.CASCADE)

    title = models.CharField(max_length=128, null=True)
    text = models.TextField(null=False)
    html = models.TextField(null=True)
    url = models.URLField(null=True)

    metadata = JSONField(null=True)

    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    upvotes = models.IntegerField(default=0, db_index=True)

    is_visible = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)

    deleted_by = models.UUIDField(null=True)

    history = HistoricalRecords(
        user_model=User,
        table_name="comments_history",
        excluded_fields=[
            "html",
            "ipaddress",
            "useragent",
            "created_at",
            "updated_at",
            "upvotes",
        ],
    )

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]

    def to_dict(self):
        return {
            "id": str(self.id),
            "upvotes": self.upvotes,
        }

    def save(self, *args, **kwargs):
        if self.reply_to:
            self.reply_to = self.find_top_comment(self.reply_to)

        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def delete(self, deleted_by=None, *args, **kwargs):
        self.is_deleted = True
        self.deleted_by = deleted_by.id
        self.save()

    def undelete(self, *args, **kwargs):
        self.is_deleted = False
        self.deleted_by = None
        self.save()

    def increment_vote_count(self):
        return Comment.objects.filter(id=self.id).update(upvotes=F("upvotes") + 1)

    @property
    def is_editable(self):
        return self.created_at >= datetime.utcnow() - settings.COMMENT_EDIT_TIMEDELTA

    @classmethod
    def visible_objects(cls):
        return cls.objects\
            .filter(is_visible=True)\
            .select_related("author", "reply_to")

    @classmethod
    def objects_for_user(cls, user):
        return cls.visible_objects().extra({
            "is_voted": "select 1 from comment_votes "
                        "where comment_votes.comment_id = comments.id "
                        f"and comment_votes.user_id = '{user.id}'"
        })

    @classmethod
    def update_post_counters(cls, post):
        post.comment_count = Comment.visible_objects().filter(post=post, is_deleted=False).count()
        post.last_activity_at = datetime.utcnow()
        post.save()

    @classmethod
    def find_top_comment(cls, comment):
        if not comment.reply_to:
            return comment

        depth = 10
        while depth > 0:
            depth -= 1
            parent = comment.reply_to
            if not parent.reply_to:
                return parent

        raise NotFound(title="Родительский коммент не найден")

    @classmethod
    def check_rate_limits(cls, user):
        if user.is_moderator:
            return True

        day_comment_count = Comment.visible_objects()\
            .filter(
                author=user, created_at__gte=datetime.utcnow() - timedelta(hours=24)
            )\
            .count()

        return day_comment_count < settings.RATE_LIMIT_COMMENTS_PER_DAY


class CommentVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="comment_votes", db_index=True, null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="comment_votes", db_index=True, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, related_name="votes", db_index=True, on_delete=models.CASCADE)

    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comment_votes"
        unique_together = [["user", "comment"]]

    @classmethod
    def upvote(cls, request, user, comment):
        if not user.is_god and user.id == comment.author_id:
            return None, False

        post_vote, is_vote_created = CommentVote.objects.get_or_create(
            user=user,
            comment=comment,
            defaults=dict(
                post=comment.post,
                ipaddress=parse_ip_address(request),
                useragent=parse_useragent(request),
            )
        )

        if is_vote_created:
            comment.increment_vote_count()
            comment.author.increment_vote_count()

        return post_vote, is_vote_created
