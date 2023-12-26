import math
from datetime import timedelta
from uuid import uuid4

from django.db import models, transaction, IntegrityError
from django.db.models import F, Count

from club.exceptions import InsufficientFunds, BadRequest, ContentDuplicated
from comments.models import Comment
from posts.models.post import Post
from users.models.user import User


class Badge(models.Model):
    code = models.CharField(primary_key=True, max_length=32, null=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    title = models.CharField(max_length=64, null=False)
    description = models.CharField(max_length=256, null=True)
    price_days = models.IntegerField(default=10)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "badges"
        ordering = ["price_days", "code"]

    def __str__(self):
        return f"Badge: {self.code}"

    @classmethod
    def visible_objects(cls):
        return cls.objects.filter(is_visible=True)


class UserBadge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    badge = models.ForeignKey(Badge, related_name="user_badges", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    from_user = models.ForeignKey(User, related_name="from_badges", null=True, on_delete=models.SET_NULL)
    to_user = models.ForeignKey(User, related_name="to_badges", on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name="post_badges", null=True, on_delete=models.SET_NULL)
    comment = models.ForeignKey(Comment, related_name="comment_badges", null=True, on_delete=models.SET_NULL)

    note = models.TextField(null=True)

    class Meta:
        db_table = "user_badges"
        unique_together = [
            ("from_user", "to_user", "badge", "post_id"),
            ("from_user", "to_user", "badge", "comment_id"),
        ]

    @classmethod
    def create_user_badge(cls, badge, from_user, to_user, post=None, comment=None, note=None):
        if from_user == to_user:
            raise BadRequest(
                title="🛑 Нельзя дарить награды самому себе",
                message="Это что такое-то вообще!"
            )

        if badge.price_days >= from_user.membership_days_left():
            raise InsufficientFunds(
                title="💸 Недостаточно средств :(",
                message=f"Вы не можете подарить юзеру эту награду, "
                        f"так как у вас осталось {math.floor(from_user.membership_days_left())} дней членства, "
                        f"а награда стоит {badge.price_days}. "
                        f"Продлите членство в настройках своего профиля."
            )

        with transaction.atomic():
            # save user badge into the database
            try:
                user_badge = UserBadge.objects.create(
                    badge=badge,
                    from_user=from_user,
                    to_user=to_user,
                    post=post,
                    comment=comment,
                    note=note,
                )
            except IntegrityError:
                raise ContentDuplicated(
                    title="🛑 Вы уже дарили награду за этот пост или комментарий",
                    message="Повторно награды дарить нельзя. Но вы можете подарить другую награду."
                )

            # deduct days balance from profile
            User.objects\
                .filter(id=from_user.id)\
                .update(
                    membership_expires_at=F("membership_expires_at") - timedelta(days=badge.price_days)
                )

            # add badge to post/comment metadata (for caching purposes)
            comment_or_post = comment or post
            metadata = comment_or_post.metadata or {}
            badges = metadata.get("badges") or {}
            if badge.code not in badges:
                # add new badge
                badges[badge.code] = {
                    "title": badge.title,
                    "description": badge.description,
                    "count": 1,
                }
            else:
                # if badge exists, increment badge count
                badges[badge.code]["count"] += 1

            # update metadata only (do not use .save(), it saves all fields and can cause side-effects)
            metadata["badges"] = badges
            type(comment_or_post).objects.filter(id=comment_or_post.id).update(metadata=metadata)

        return user_badge

    @classmethod
    def user_badges(cls, user):
        return UserBadge.objects.filter(to_user=user).select_related("badge").order_by("-created_at")

    @classmethod
    def user_badges_grouped(cls, user):
        badges = {
            badge.code: badge for badge in Badge.visible_objects()
        }

        badge_groups = UserBadge.objects\
            .filter(to_user=user)\
            .order_by("badge_id")\
            .values("badge_id")\
            .annotate(count=Count("badge_id"))

        return {
            badge_group["badge_id"]: {
                "title": badges[badge_group["badge_id"]].title,
                "description": badges[badge_group["badge_id"]].description,
                "count": badge_group["count"],
            } for badge_group in badge_groups
        }
