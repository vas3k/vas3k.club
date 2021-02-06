from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import F
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils.html import strip_tags
from simple_history.models import HistoricalRecords

from common.models import ModelDiffMixin
from posts.models.topics import Topic
from users.models.user import User
from utils.slug import generate_unique_slug


class Post(models.Model, ModelDiffMixin):
    TYPE_POST = "post"
    TYPE_INTRO = "intro"
    TYPE_LINK = "link"
    TYPE_QUESTION = "question"
    TYPE_PAIN = "pain"
    TYPE_IDEA = "idea"
    TYPE_PROJECT = "project"
    TYPE_EVENT = "event"
    TYPE_REFERRAL = "referral"
    TYPE_BATTLE = "battle"
    TYPE_WEEKLY_DIGEST = "weekly_digest"
    TYPES = [
        (TYPE_POST, "Текст"),
        (TYPE_INTRO, "#intro"),
        (TYPE_LINK, "Ссылка"),
        (TYPE_QUESTION, "Вопрос"),
        (TYPE_PAIN, "Боль"),
        (TYPE_IDEA, "Идея"),
        (TYPE_PROJECT, "Проект"),
        (TYPE_EVENT, "Событие"),
        (TYPE_REFERRAL, "Рефералка"),
        (TYPE_BATTLE, "Батл"),
        (TYPE_WEEKLY_DIGEST, "Журнал Клуба"),
    ]

    TYPE_TO_EMOJI = {
        TYPE_POST: "📝",
        TYPE_INTRO: "🙋‍♀️",
        TYPE_LINK: "🔗",
        TYPE_QUESTION: "❓",
        TYPE_PAIN: "😭",
        TYPE_IDEA: "💡",
        TYPE_PROJECT: "🏗",
        TYPE_EVENT: "📅",
        TYPE_REFERRAL: "🏢",
        TYPE_BATTLE: "🤜🤛"
    }

    TYPE_TO_PREFIX = {
        TYPE_POST: "",
        TYPE_INTRO: "#intro",
        TYPE_LINK: "➜",
        TYPE_PAIN: "Боль:",
        TYPE_IDEA: "Идея:",
        TYPE_QUESTION: "Вопрос:",
        TYPE_PROJECT: "Проект:",
        TYPE_EVENT: "Событие:",
        TYPE_REFERRAL: "Рефералка:",
        TYPE_BATTLE: "Батл:"
    }

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    slug = models.CharField(max_length=128, unique=True, db_index=True)

    author = models.ForeignKey(User, related_name="posts", db_index=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=32, choices=TYPES, default=TYPE_POST, db_index=True)
    topic = models.ForeignKey(Topic, related_name="posts", null=True, db_index=True, on_delete=models.SET_NULL)
    label = models.JSONField(null=True)

    title = models.TextField(null=False)
    text = models.TextField(null=False)
    html = models.TextField(null=True)
    url = models.URLField(max_length=1024, null=True)
    image = models.URLField(max_length=1024, null=True)

    metadata = models.JSONField(null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)
    published_at = models.DateTimeField(null=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, db_index=True)

    comment_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0, db_index=True)
    hotness = models.IntegerField(default=0, db_index=True)

    is_visible = models.BooleanField(default=False)  # published or draft
    is_visible_on_main_page = models.BooleanField(default=True)  # main page or room-only post
    is_commentable = models.BooleanField(default=True)  # allow comments
    is_approved_by_moderator = models.BooleanField(default=False)  # expose in newsletters, rss, etc
    is_public = models.BooleanField(default=False)  # visible for the outside world
    is_pinned_until = models.DateTimeField(null=True)  # pin on top of the main feed
    is_shadow_banned = models.BooleanField(default=False)  # hide from main page

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
        ],
    )

    class Meta:
        db_table = "posts"
        ordering = ["-created_at"]

    def to_dict(self):
        return {
            "id": str(self.id),
            "type": self.type,
            "slug": self.slug,
            "author_slug": self.author.slug,
            "title": self.title,
            "text": self.text,
            "upvotes": self.upvotes,
            "metadata": self.metadata,
            "published_at": self.published_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_activity_at": self.last_activity_at.isoformat(),
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
        return Post.objects.filter(id=self.id).update(upvotes=F("upvotes") + 1)

    def decrement_vote_count(self):
        return Post.objects.filter(id=self.id).update(upvotes=F("upvotes") - 1)

    @property
    def emoji(self):
        return self.TYPE_TO_EMOJI.get(self.type) or ""

    @property
    def prefix(self):
        return self.TYPE_TO_PREFIX.get(self.type) or ""

    @property
    def is_pinned(self):
        return self.is_pinned_until and self.is_pinned_until > datetime.utcnow()

    @property
    def is_searchable(self):
        return self.is_visible and not self.is_shadow_banned

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
    def check_duplicate(cls, user, title):
        latest_user_post = Post.objects.filter(author=user).order_by("-created_at").first()
        return latest_user_post and latest_user_post.title == title

    @classmethod
    def visible_objects(cls):
        return cls.objects.filter(is_visible=True).select_related("topic", "author")

    @classmethod
    def objects_for_user(cls, user):
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

