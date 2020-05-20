from datetime import datetime, timedelta
from uuid import uuid4

from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from django.db.models import F, Q
from slugify import slugify

from common.data.colors import COOL_COLORS
from common.data.expertise import EXPERTISE
from utils.models import ModelDiffMixin
from utils.slug import generate_unique_slug
from utils.strings import random_string


class User(models.Model, ModelDiffMixin):
    MEMBERSHIP_PLATFORM_PATREON = "patreon"
    MEMBERSHIP_PLATFORMS = [
        (MEMBERSHIP_PLATFORM_PATREON, "Patreon"),
    ]

    MEMBERSHIP_TYPE_NORMAL = "normal"
    MEMBERSHIP_TYPE_PRO = "pro"
    MEMBERSHIP_TYPE_LIFETIME = "lifetime"
    MEMBERSHIP_TYPES = [
        (MEMBERSHIP_TYPE_NORMAL, "Normal"),
        (MEMBERSHIP_TYPE_PRO, "Pro"),
        (MEMBERSHIP_TYPE_LIFETIME, "Lifetime"),
    ]

    EMAIL_DIGEST_TYPE_NOPE = "nope"
    EMAIL_DIGEST_TYPE_DAILY = "daily"
    EMAIL_DIGEST_TYPE_WEEKLY = "weekly"
    EMAIL_DIGEST_TYPES = [
        (EMAIL_DIGEST_TYPE_NOPE, "Nothing"),
        (EMAIL_DIGEST_TYPE_DAILY, "Daily"),
        (EMAIL_DIGEST_TYPE_WEEKLY, "Weekly"),
    ]

    ROLE_MODERATOR = "moderator"
    ROLE_GOD = "god"
    ROLES = [
        (ROLE_MODERATOR, "Модератор"),
        (ROLE_GOD, "Режим Бога")
    ]

    DEFAULT_AVATAR = "https://i.vas3k.club/v.png"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    slug = models.CharField(max_length=32, unique=True)
    card_number = models.IntegerField(default=0)

    email = models.EmailField()
    full_name = models.CharField(max_length=128, null=False)
    avatar = models.URLField(null=True, blank=True)
    secret_hash = models.CharField(max_length=16, db_index=True)

    company = models.TextField(null=True)
    position = models.TextField(null=True)
    city = models.CharField(max_length=128, null=True)
    country = models.CharField(max_length=128, null=True)
    geo_id = models.IntegerField(null=True)
    bio = models.TextField(null=True)
    hat = JSONField(null=True)

    balance = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    membership_started_at = models.DateTimeField(null=False)
    membership_expires_at = models.DateTimeField(null=False)
    membership_platform_type = models.CharField(max_length=128, choices=MEMBERSHIP_PLATFORMS,
                                                default=MEMBERSHIP_PLATFORM_PATREON, null=False)
    membership_platform_id = models.CharField(max_length=128, unique=True)
    membership_platform_data = JSONField(null=True)
    membership_type = models.CharField(max_length=16, choices=MEMBERSHIP_TYPES,
                                       default=MEMBERSHIP_TYPE_NORMAL, null=False)

    email_digest_type = models.CharField(max_length=16, choices=EMAIL_DIGEST_TYPES,
                                         default=EMAIL_DIGEST_TYPE_WEEKLY, null=False)

    telegram_id = models.CharField(max_length=128, null=True)
    telegram_data = JSONField(null=True)

    is_email_verified = models.BooleanField(default=False)
    is_email_unsubscribed = models.BooleanField(default=False)
    is_profile_complete = models.BooleanField(default=False)
    is_profile_reviewed = models.BooleanField(default=False)
    is_profile_rejected = models.BooleanField(default=False)
    is_banned_until = models.DateTimeField(null=True)

    roles = ArrayField(models.CharField(max_length=32, choices=ROLES), default=list, null=False)

    class Meta:
        db_table = "users"

    def save(self, *args, **kwargs):
        if not self.secret_hash:
            self.secret_hash = random_string(length=10)

        if not self.slug:
            self.slug = generate_unique_slug(User, self.full_name, separator="")

        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def update_last_activity(self):
        now = datetime.utcnow()
        if self.last_activity_at < now - timedelta(minutes=5):
            return User.objects.filter(id=self.id).update(last_activity_at=now)

    def membership_days(self):
        if self.membership_started_at:
            return int(
                (datetime.utcnow() - self.membership_started_at).total_seconds() / 60 / 60 / 24
            )
        return None

    def increment_vote_count(self):
        return User.objects.filter(id=self.id).update(upvotes=F("upvotes") + 1)

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
        return self.is_profile_complete \
               and not self.is_banned \
               and self.is_profile_reviewed \
               and not self.is_profile_rejected


class Tag(models.Model):
    GROUP_HOBBIES = "hobbies"
    GROUP_PERSONAL = "personal"
    GROUP_TECH = "tech"
    GROUP_OTHER = "other"
    GROUPS = [
        (GROUP_PERSONAL, "О себе"),
        (GROUP_TECH, "Технологии"),
        (GROUP_HOBBIES, "Хобби"),
        (GROUP_OTHER, "Остальное"),
    ]

    code = models.CharField(primary_key=True, max_length=32, null=False, unique=True)
    group = models.CharField(max_length=32, choices=GROUPS, default=GROUP_OTHER, null=False)
    name = models.CharField(max_length=64, null=False)

    index = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "tags"
        ordering = ["-group", "index"]

    def to_dict(self):
        return {
            "code": self.code,
            "group": self.group,
            "name": self.name,
            "color": self.color,
        }

    @property
    def color(self):
        return COOL_COLORS[sum(map(ord, self.code)) % len(COOL_COLORS)]

    def group_display(self):
        return dict(Tag.GROUPS).get(self.group) or Tag.GROUP_OTHER


class UserTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="tags", on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, related_name="user_tags", on_delete=models.CASCADE)
    name = models.CharField(max_length=64, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_tags"
        unique_together = [["tag", "user"]]


class UserBadge(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        User, related_name="achievements", db_index=True, on_delete=models.CASCADE
    )

    type = models.CharField(max_length=32, null=False)
    name = models.CharField(max_length=64, null=False)
    description = models.CharField(max_length=256, null=True)
    image = models.URLField(null=False)
    style = models.CharField(max_length=256, default="", null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_achievements"
        unique_together = [["type", "user"]]


class UserExpertise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="expertise", on_delete=models.CASCADE)
    expertise = models.CharField(max_length=32, null=False, db_index=True)
    name = models.CharField(max_length=64, null=False)
    value = models.IntegerField(default=0, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_expertise"
        unique_together = [["expertise", "user"]]
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        pre_defined_expertise = dict(sum([e[1] for e in EXPERTISE], []))  # flatten nested items

        if not self.name:
            self.name = pre_defined_expertise.get(self.expertise) or self.expertise

        if self.expertise not in pre_defined_expertise:
            self.expertise = slugify(self.expertise.lower())

        return super().save(*args, **kwargs)

    @property
    def color(self):
        return COOL_COLORS[hash(self.name) % len(COOL_COLORS)]


class Geo(models.Model):
    id = models.AutoField(primary_key=True)
    country_en = models.CharField(max_length=256)
    region_en = models.CharField(max_length=256)
    city_en = models.CharField(max_length=256, db_index=True)
    country = models.CharField(max_length=256)
    region = models.CharField(max_length=256)
    city = models.CharField(max_length=256, db_index=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    population = models.IntegerField(default=0)

    class Meta:
        db_table = "geo"
        ordering = ["id"]

    @classmethod
    def update_for_user(cls, user):
        user.geo_id = Geo.objects.filter(
            Q(country=user.country) &
            (Q(city__iexact=user.city) | Q(city_en__iexact=user.city))
        ).order_by("id").first()
        user.save()
