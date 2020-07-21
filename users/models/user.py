from datetime import datetime, timedelta
from uuid import uuid4

from django.contrib.postgres.fields import JSONField, ArrayField
from django.db import models
from django.db.models import F

from users.models.geo import Geo
from common.models import ModelDiffMixin
from utils.slug import generate_unique_slug
from utils.strings import random_hash


class User(models.Model, ModelDiffMixin):
    MEMBERSHIP_PLATFORM_DIRECT = "direct"
    MEMBERSHIP_PLATFORM_PATREON = "patreon"
    MEMBERSHIP_PLATFORMS = [
        (MEMBERSHIP_PLATFORM_DIRECT, "Direct"),
        (MEMBERSHIP_PLATFORM_PATREON, "Patreon"),
    ]

    EMAIL_DIGEST_TYPE_NOPE = "nope"
    EMAIL_DIGEST_TYPE_DAILY = "daily"
    EMAIL_DIGEST_TYPE_WEEKLY = "weekly"
    EMAIL_DIGEST_TYPES = [
        (EMAIL_DIGEST_TYPE_NOPE, "Nothing"),
        (EMAIL_DIGEST_TYPE_DAILY, "Daily"),
        (EMAIL_DIGEST_TYPE_WEEKLY, "Weekly"),
    ]

    ROLE_CURATOR = "curator"
    ROLE_MODERATOR = "moderator"
    ROLE_GOD = "god"
    ROLES = [
        (ROLE_CURATOR, "Куратор"),
        (ROLE_MODERATOR, "Модератор"),
        (ROLE_GOD, "Бог")
    ]

    MODERATION_STATUS_INTRO = "intro"
    MODERATION_STATUS_ON_REVIEW = "on_review"
    MODERATION_STATUS_REJECTED = "rejected"
    MODERATION_STATUS_APPROVED = "approved"
    MODERATION_STATUSES = [
        (MODERATION_STATUS_INTRO, MODERATION_STATUS_INTRO),
        (MODERATION_STATUS_ON_REVIEW, MODERATION_STATUS_ON_REVIEW),
        (MODERATION_STATUS_REJECTED, MODERATION_STATUS_REJECTED),
        (MODERATION_STATUS_APPROVED, MODERATION_STATUS_APPROVED),
    ]

    DEFAULT_AVATAR = "https://i.vas3k.club/v.png"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    slug = models.CharField(max_length=32, unique=True)
    card_number = models.IntegerField(default=0)

    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=128, null=False)
    avatar = models.URLField(null=True, blank=True)
    secret_hash = models.CharField(max_length=16, db_index=True)

    company = models.TextField(null=True)
    position = models.TextField(null=True)
    city = models.CharField(max_length=128, null=True)
    country = models.CharField(max_length=128, null=True)
    geo = models.ForeignKey(Geo, on_delete=models.SET_NULL, null=True)
    bio = models.TextField(null=True)
    contact = models.CharField(max_length=256, null=True)
    hat = JSONField(null=True)

    balance = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    membership_started_at = models.DateTimeField(null=False)
    membership_expires_at = models.DateTimeField(null=False)
    membership_platform_type = models.CharField(
        max_length=128, choices=MEMBERSHIP_PLATFORMS,
        default=MEMBERSHIP_PLATFORM_PATREON, null=False
    )
    patreon_id = models.CharField(max_length=128, null=True, unique=True)
    membership_platform_data = JSONField(null=True)

    email_digest_type = models.CharField(
        max_length=16, choices=EMAIL_DIGEST_TYPES,
        default=EMAIL_DIGEST_TYPE_WEEKLY, null=False
    )

    telegram_id = models.CharField(max_length=128, null=True)
    telegram_data = JSONField(null=True)

    stripe_id = models.CharField(max_length=128, null=True)

    is_email_verified = models.BooleanField(default=False)
    is_email_unsubscribed = models.BooleanField(default=False)
    is_banned_until = models.DateTimeField(null=True)

    moderation_status = models.CharField(
        max_length=32, choices=MODERATION_STATUSES,
        default=MODERATION_STATUS_INTRO, null=False,
        db_index=True
    )

    roles = ArrayField(models.CharField(max_length=32, choices=ROLES), default=list, null=False)

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        if not self.secret_hash:
            self.secret_hash = random_hash(length=16)

        if not self.slug:
            self.slug = generate_unique_slug(User, self.full_name, separator="")

        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def to_dict(self):
        return {
            "slug": self.slug,
            "full_name": self.full_name,
            "avatar": self.avatar,
            "moderation_status": self.moderation_status,
            "payment_status": "active" if self.membership_expires_at >= datetime.utcnow() else "inactive",
        }

    def update_last_activity(self):
        now = datetime.utcnow()
        if self.last_activity_at < now - timedelta(minutes=5):
            return User.objects.filter(id=self.id).update(last_activity_at=now)

    def membership_days_left(self):
        return (self.membership_expires_at - datetime.utcnow()).total_seconds() // 60 // 60 / 24

    def membership_years_left(self):
        return self.membership_days_left() / 365

    def increment_vote_count(self):
        return User.objects.filter(id=self.id).update(upvotes=F("upvotes") + 1)

    def decrement_vote_count(self):
        return User.objects.filter(id=self.id).update(upvotes=F("upvotes") - 1)

    def get_avatar(self):
        return self.avatar or self.DEFAULT_AVATAR

    @property
    def is_banned(self):
        if self.is_god:
            return False
        return self.is_banned_until and self.is_banned_until > datetime.utcnow()

    @property
    def is_god(self):
        return self.roles and self.ROLE_GOD in self.roles

    @property
    def is_moderator(self):
        return (self.roles and self.ROLE_MODERATOR in self.roles) or self.is_god

    @property
    def is_club_member(self):
        return self.moderation_status == User.MODERATION_STATUS_APPROVED and not self.is_banned

    @property
    def is_paid_member(self):
        return self.is_club_member and self.membership_expires_at >= datetime.utcnow()

    @property
    def secret_auth_code(self):
        return f"{self.email}|-{self.secret_hash}"

    @classmethod
    def registered_members(cls):
        return cls.objects.filter(
            moderation_status=User.MODERATION_STATUS_APPROVED
        )
