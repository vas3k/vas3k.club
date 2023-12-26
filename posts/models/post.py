from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils.html import strip_tags
from simple_history.models import HistoricalRecords

from common.data.labels import LABELS
from common.models import ModelDiffMixin
from rooms.models import Room
from users.models.user import User
from utils.slug import generate_unique_slug


class Post(models.Model, ModelDiffMixin):
    TYPE_POST = "post"
    TYPE_INTRO = "intro"
    TYPE_LINK = "link"
    TYPE_QUESTION = "question"
    TYPE_IDEA = "idea"
    TYPE_PROJECT = "project"
    TYPE_EVENT = "event"
    TYPE_BATTLE = "battle"
    TYPE_WEEKLY_DIGEST = "weekly_digest"
    TYPE_GUIDE = "guide"
    TYPE_THREAD = "thread"
    TYPES = [
        (TYPE_POST, "Текст"),
        (TYPE_INTRO, "#intro"),
        (TYPE_LINK, "Ссылка"),
        (TYPE_QUESTION, "Вопрос"),
        (TYPE_IDEA, "Идея"),
        (TYPE_PROJECT, "Проект"),
        (TYPE_EVENT, "Событие"),
        (TYPE_BATTLE, "Батл"),
        (TYPE_WEEKLY_DIGEST, "Журнал Клуба"),
        (TYPE_GUIDE, "Путеводитель"),
        (TYPE_THREAD, "Тред"),
    ]

    TYPE_TO_EMOJI = {
        TYPE_POST: "📝",
        TYPE_INTRO: "🙋‍♀️",
        TYPE_LINK: "🔗",
        TYPE_QUESTION: "❓",
        TYPE_IDEA: "💡",
        TYPE_PROJECT: "🏗",
        TYPE_EVENT: "📅",
        TYPE_BATTLE: "🤜🤛",
        TYPE_GUIDE: "🗺",
        TYPE_THREAD: "🗄",
    }

    TYPE_TO_PREFIX = {
        TYPE_POST: "",
        TYPE_INTRO: "Интро",
        TYPE_LINK: "➜",
        TYPE_IDEA: "Идея:",
        TYPE_QUESTION: "Вопрос:",
        TYPE_PROJECT: "Проект:",
        TYPE_EVENT: "Событие:",
        TYPE_BATTLE: "Батл:",
        TYPE_GUIDE: "🗺",
        TYPE_THREAD: "Тред:",
    }

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    slug = models.CharField(max_length=128, unique=True, db_index=True)

    author = models.ForeignKey(User, related_name="posts", db_index=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=32, choices=TYPES, default=TYPE_POST, db_index=True)
    room = models.ForeignKey(Room, related_name="posts", null=True, db_index=True, on_delete=models.SET_NULL)
    label_code = models.CharField(max_length=16, null=True, db_index=True)
    collectible_tag_code = models.CharField(max_length=32, null=True)
    coauthors = ArrayField(models.CharField(max_length=32), default=list, null=False, db_index=True)

    title = models.TextField(null=False)
    text = models.TextField(null=False)
    html = models.TextField(null=True)
    url = models.URLField(max_length=1024, null=True)
    image = models.URLField(max_length=1024, null=True)

    metadata = models.JSONField(null=True)
    comment_template = models.TextField(null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)
    published_at = models.DateTimeField(null=True, db_index=True)
    deleted_at = models.DateTimeField(null=True)

    comment_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0, db_index=True)
    hotness = models.IntegerField(default=0, db_index=True)

    is_visible = models.BooleanField(default=False)  # published or draft
    is_visible_in_feeds = models.BooleanField(default=True)  # hide post from main feeds (still visible in rooms)
    is_commentable = models.BooleanField(default=True)  # allow comments
    is_approved_by_moderator = models.BooleanField(default=False)  # post is exposed in newsletters, rss, etc
    is_public = models.BooleanField(default=False)  # post is visible for the outside world
    is_pinned_until = models.DateTimeField(null=True)  # pin on top on the main page
    is_shadow_banned = models.BooleanField(default=False)  # hide from feeds but not for author

    history = HistoricalRecords(
        user_model=User,
        table_name="posts_history",
        excluded_fields=[
            "html",
            "created_at",
            "updated_at",
            "last_activity_at",
            "published_at",
            "comment_count",
            "view_count",
            "upvotes",
            "hotness",
            "label_code",
            "is_approved_by_moderator",
            "is_commentable",
            "is_visible_in_feeds",
            "is_pinned_until",
            "is_shadow_banned",
            "room",
        ],
    )

    class Meta:
        db_table = "posts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post: {self.title}"

    def to_dict(self, including_private=False):
        return {
            "id": self.id,
            "url": f"{settings.APP_HOST}{self.get_absolute_url()}",
            "title": self.title,
            "content_text": self.text if self.is_public or including_private else "🔒",
            "date_published": self.published_at.astimezone().isoformat(),
            "date_modified": self.updated_at.astimezone().isoformat(),
            "authors": [
                {
                    "name": self.author.full_name,
                    "url": f"{settings.APP_HOST}{self.author.get_absolute_url()}",
                    "avatar": self.author.get_avatar()
                }
            ],
            "_club": {
                "type": self.type,
                "slug": self.slug,
                "coauthors": self.coauthors,
                "comment_count": self.comment_count,
                "view_count": self.view_count,
                "upvotes": self.upvotes,
                "is_public": self.is_public,
                "is_commentable": self.is_commentable,
            }
        }

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Post, str(Post.objects.count()))

        if not self.published_at and self.is_visible:
            self.published_at = datetime.utcnow()

        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("show_post", kwargs={"post_type": self.type, "post_slug": self.slug})

    def increment_view_count(self):
        return Post.objects.filter(id=self.id).update(view_count=F("view_count") + 1)

    def increment_vote_count(self):
        if self.coauthors:
            self.increment_coauthors_vote_count()
        return Post.objects.filter(id=self.id).update(upvotes=F("upvotes") + 1)

    def decrement_vote_count(self):
        if self.coauthors:
            self.decrement_coauthors_vote_count()
        return Post.objects.filter(id=self.id).update(upvotes=F("upvotes") - 1)

    def increment_coauthors_vote_count(self):
        return User.objects.filter(slug__in=self.coauthors).update(upvotes=F("upvotes") + 1)

    def decrement_coauthors_vote_count(self):
        return User.objects.filter(slug__in=self.coauthors, upvotes__gt=0).update(upvotes=F("upvotes") - 1)

    def can_edit(self, user):
        if not user:
            return False
        return self.author == user or user.is_moderator or user.slug in self.coauthors

    def can_view(self, user):
        return self.is_visible or self.can_view_draft(user)

    def can_view_draft(self, user):
        if not user:
            return False
        return self.can_edit(user) or user.is_curator

    @property
    def emoji(self):
        return self.TYPE_TO_EMOJI.get(self.type) or ""

    @property
    def prefix(self):
        return self.TYPE_TO_PREFIX.get(self.type) or ""

    @property
    def label(self):
        lbl = LABELS.get(self.label_code)
        if lbl is not None:
            lbl['code'] = self.label_code
        return lbl

    @property
    def coauthors_with_details(self):
        return User.objects.filter(slug__in=self.coauthors).all()

    @property
    def is_pinned(self):
        return self.is_pinned_until and self.is_pinned_until > datetime.utcnow()

    @property
    def is_searchable(self):
        return self.is_visible and not self.is_shadow_banned

    @property
    def is_approved(self):
        return self.is_approved_by_moderator or self.upvotes >= settings.COMMUNITY_APPROVE_UPVOTES

    @property
    def is_safely_deletable_by_author(self):
        return self.comment_count < settings.MAX_COMMENTS_FOR_DELETE_VS_CLEAR

    @property
    def description(self):
        return truncatechars(strip_tags(self.html or ""), 400)

    @property
    def effective_published_at(self):
        return self.published_at or self.created_at

    @property
    def event_datetime(self):
        if self.metadata and self.metadata.get("event"):
            hour, minute, second = map(int, self.metadata["event"]["time"].split(":", 2))
            day = int(self.metadata["event"].get("day") or 0)
            month = int(self.metadata["event"].get("month") or self.effective_published_at.month)
            if month < self.effective_published_at.month:
                year = self.effective_published_at.year + 1
            else:
                year = self.effective_published_at.year
            return datetime(year, month, day, hour, minute, second)

    @classmethod
    def check_duplicate(cls, user, title, ignore_post_id=None):
        last_post = Post.objects\
            .filter(author=user) \
            .order_by("-created_at")\
            .first()
        return last_post and last_post.id != ignore_post_id and last_post.title == title

    @classmethod
    def visible_objects(cls):
        return cls.objects.filter(is_visible=True).select_related("room", "author")

    @classmethod
    def objects_for_user(cls, user):
        if not user:
            return cls.visible_objects()

        return cls.visible_objects()\
            .extra({
                "is_voted": "select 1 from post_votes "
                            "where post_votes.post_id = posts.id "
                            f"and post_votes.user_id = '{user.id}'",
                "upvoted_at": "select ROUND(extract(epoch from created_at) * 1000) from post_votes "
                              "where post_votes.post_id = posts.id "
                              f"and post_votes.user_id = '{user.id}'",
                "unread_comments": f"select unread_comments from post_views "
                                   f"where post_views.post_id = posts.id "
                                   f"and post_views.user_id = '{user.id}'"
            })  # TODO: i've been trying to use .annotate() here for 2 hours and I have no idea why it's not working

    @classmethod
    def check_rate_limits(cls, user):
        if user.is_moderator:
            return True

        day_post_count = Post.visible_objects()\
            .filter(author=user, created_at__gte=datetime.utcnow() - timedelta(hours=24))\
            .count()

        return day_post_count < settings.RATE_LIMIT_POSTS_PER_DAY

    @classmethod
    def get_user_intro(cls, user):
        return cls.objects.filter(author=user, type=Post.TYPE_INTRO).first()

    @classmethod
    def upsert_user_intro(cls, user, text, is_visible=True):
        intro, is_created = cls.objects.update_or_create(
            author=user,
            type=cls.TYPE_INTRO,
            defaults=dict(
                slug=user.slug,
                title=f"#intro от @{user.slug}",
                text=text,
                is_visible=is_visible,
                is_public=False,
            ),
        )
        if not is_created:
            intro.html = None
            intro.save()

        return intro

    def clear(self):
        self.text = settings.CLEARED_POST_TEXT
        self.html = None
        self.author = User.objects.filter(slug=settings.DELETED_USERNAME).first()
        self.save()

    def publish(self):
        self.is_visible = True
        self.published_at = datetime.utcnow()
        self.save()

    def unpublish(self):
        self.is_visible = False
        self.published_at = None
        self.save()

    def delete(self, *args, **kwargs):
        self.deleted_at = datetime.utcnow()
        self.save()

    def undelete(self, *args, **kwargs):
        self.deleted_at = None
        self.save()
