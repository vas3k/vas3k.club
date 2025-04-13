from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import F
from simple_history.models import HistoricalRecords

from club.exceptions import NotFound, BadRequest
from common.request import parse_ip_address
from posts.models.post import Post
from users.models.user import User


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    author = models.ForeignKey(User, related_name="comments", null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)

    reply_to = models.ForeignKey("self", related_name="replies", null=True, on_delete=models.CASCADE)

    title = models.CharField(max_length=128, null=True)
    text = models.TextField(null=False)
    html = models.TextField(null=True)
    url = models.URLField(max_length=1024, null=True)

    metadata = models.JSONField(null=True)

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
            "post",
            "html",
            "reply_to",
            "ipaddress",
            "useragent",
            "created_at",
            "updated_at",
            "upvotes",
            "is_visible",
            "is_deleted",
            "is_pinned",
        ],
    )

    class Meta:
        db_table = "comments"
        ordering = ["created_at"]

    def to_dict(self):
        return {
            "id": str(self.id),
            "text": self.text,
            "author": self.author.to_dict(),
            "reply_to_id": self.reply_to_id,
            "upvotes": self.upvotes,
            "created_at": self.created_at.isoformat(),
        }

    def save(self, *args, **kwargs):
        if self.reply_to and self.reply_to.reply_to and self.reply_to.reply_to.reply_to_id:
            raise BadRequest(message="3 уровня комментариев это максимум")

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

    def decrement_vote_count(self):
        return Comment.objects.filter(id=self.id).update(upvotes=F("upvotes") - 1)

    @property
    def battle_side(self):
        if self.metadata:
            side_code = self.metadata.get("battle", {}).get("side")
            if side_code:
                return self.post.metadata["battle"]["sides"][side_code]["name"]

        return None

    @property
    def is_editable(self):
        return self.created_at >= datetime.utcnow() - settings.COMMENT_EDITABLE_TIMEDELTA

    def is_deletable_by(self, user):
        if user == self.author:
            return self.created_at >= datetime.utcnow() - settings.COMMENT_DELETABLE_TIMEDELTA

        if user == self.post.author:
            return self.created_at >= datetime.utcnow() - settings.COMMENT_DELETABLE_BY_POST_AUTHOR_TIMEDELTA

        return user.is_moderator

    @classmethod
    def visible_objects(cls, show_deleted=False):
        comments = cls.objects\
            .filter(is_visible=True)\
            .select_related("author", "post", "reply_to")

        if not show_deleted:
            comments = comments.filter(deleted_by__isnull=True)

        return comments

    @classmethod
    def objects_for_user(cls, user):
        return cls.visible_objects(show_deleted=True).extra({
            "is_voted": "select 1 from comment_votes "
                        "where comment_votes.comment_id = comments.id "
                        f"and comment_votes.user_id = '{user.id}'",
            "upvoted_at": "select ROUND(extract(epoch from created_at) * 1000) from comment_votes "
                          "where comment_votes.comment_id = comments.id "
                          f"and comment_votes.user_id = '{user.id}'",
        })

    @classmethod
    def update_post_counters(cls, post, update_activity=True):
        post.comment_count = Comment.visible_objects().filter(post=post, is_deleted=False).count()
        if update_activity:
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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "comment_votes"
        unique_together = [["user", "comment"]]

    @property
    def is_retractable(self):
        return self.created_at >= datetime.utcnow() - settings.RETRACT_VOTE_TIMEDELTA

    @classmethod
    def upvote(cls, user, comment, request=None):
        if not user.is_god and user.id == comment.author_id:
            return None, False

        post_vote, is_vote_created = CommentVote.objects.get_or_create(
            user=user,
            comment=comment,
            defaults=dict(
                post=comment.post,
                ipaddress=parse_ip_address(request) if request else None,
            )
        )

        if is_vote_created:
            comment.increment_vote_count()
            comment.author.increment_vote_count()

        return post_vote, is_vote_created

    @classmethod
    def retract_vote(cls, request, user, comment):
        if not user.is_god and user.id == comment.author_id:
            return False

        try:
            comment_vote = CommentVote.objects.get(
                user=user,
                comment=comment
            )

            if not comment_vote.is_retractable:
                return False

            is_vote_deleted, _ = comment_vote.delete()
            if is_vote_deleted:
                comment.decrement_vote_count()
                comment.author.decrement_vote_count()

                return True if is_vote_deleted > 0 else False
        except CommentVote.DoesNotExist:
            return False
