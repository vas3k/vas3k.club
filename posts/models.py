from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import F
from django.template.defaultfilters import truncatechars
from django.utils.html import strip_tags
from simple_history.models import HistoricalRecords

from common.request import parse_ip_address, parse_useragent
from users.models import User
from utils.models import ModelDiffMixin
from utils.slug import generate_unique_slug


class Topic(models.Model):
    slug = models.CharField(primary_key=True, max_length=32, unique=True)

    name = models.CharField(max_length=64, null=False)
    icon = models.URLField(null=True)
    description = models.TextField(null=True)
    color = models.CharField(max_length=16, null=False)
    style = models.CharField(max_length=256, default="", null=True)

    last_activity_at = models.DateTimeField(auto_now_add=True, null=False)

    is_visible = models.BooleanField(default=True)
    is_visible_on_main_page = models.BooleanField(default=True)

    class Meta:
        db_table = "topics"
        ordering = ["-last_activity_at"]

    def __str__(self):
        return self.name

    def update_last_activity(self):
        now = datetime.utcnow()
        if self.last_activity_at < now - timedelta(minutes=5):
            return Topic.objects.filter(slug=self.slug).update(last_activity_at=now)


class Post(models.Model, ModelDiffMixin):
    TYPE_POST = "post"
    TYPE_INTRO = "intro"
    TYPE_LINK = "link"
    TYPE_QUESTION = "question"
    TYPE_PAIN = "pain"
    TYPE_PROJECT = "project"
    TYPE_REFERRAL = "referral"
    TYPE_BATTLE = "battle"
    TYPE_WEEKLY_DIGEST = "weekly_digest"
    TYPES = [
        (TYPE_POST, "Текст"),
        (TYPE_INTRO, "#intro"),
        (TYPE_LINK, "Ссылка"),
        (TYPE_QUESTION, "Вопрос"),
        (TYPE_PAIN, "Расскажи где болит"),
        (TYPE_PROJECT, "Проект"),
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
        TYPE_PROJECT: "🏗",
        TYPE_REFERRAL: "🏢",
        TYPE_BATTLE: "🌗"
    }

    TYPE_TO_PREFIX = {
        TYPE_POST: "",
        TYPE_INTRO: "Интро️:",
        TYPE_LINK: "➜",
        TYPE_PAIN: "Боль:",
        TYPE_QUESTION: "Вопрос:",
        TYPE_PROJECT: "Проект:",
        TYPE_REFERRAL: "Рефералка:",
        TYPE_BATTLE: "Батл:"
    }

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    slug = models.CharField(max_length=128, unique=True, db_index=True)

    author = models.ForeignKey(User, related_name="posts", db_index=True, on_delete=models.CASCADE)
    type = models.CharField(max_length=32, choices=TYPES, default=TYPE_POST, db_index=True)
    topic = models.ForeignKey(Topic, related_name="posts", null=True, db_index=True, on_delete=models.SET_NULL)
    label = JSONField(null=True)

    title = models.TextField(null=False)
    text = models.TextField(null=False)
    html = models.TextField(null=True)
    url = models.URLField(null=True)
    image = models.URLField(null=True)

    metadata = JSONField(null=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(auto_now_add=True, db_index=True)

    comment_count = models.IntegerField(default=0)
    view_count = models.IntegerField(default=0)
    upvotes = models.IntegerField(default=0, db_index=True)

    is_visible = models.BooleanField(default=True)
    is_visible_on_main_page = models.BooleanField(default=True)
    is_commentable = models.BooleanField(default=True)
    is_approved_by_moderator = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    is_pinned_until = models.DateTimeField(null=True)
    is_shadow_banned = models.BooleanField(default=False)

    history = HistoricalRecords(
        user_model=User,
        table_name="posts_history",
        excluded_fields=[
            "html",
            "created_at",
            "updated_at",
            "last_activity_at",
            "comment_count",
            "view_count",
            "upvotes",
        ],
    )

    class Meta:
        db_table = "posts"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(Post, str(Post.objects.count()))

        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def increment_view_count(self):
        return Post.objects.filter(id=self.id).update(view_count=F("view_count") + 1)

    def increment_vote_count(self):
        return Post.objects.filter(id=self.id).update(upvotes=F("upvotes") + 1)

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
    def description(self):
        return truncatechars(strip_tags(self.html or ""), 400)

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
        return intro


class PostVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="post_votes", db_index=True, null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="voters", db_index=True, on_delete=models.CASCADE)

    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "post_votes"
        unique_together = [["user", "post"]]

    @classmethod
    def upvote(cls, request, user, post):
        if user.id == post.author_id:
            return None, False

        post_vote, is_vote_created = PostVote.objects.get_or_create(
            user=user,
            post=post,
            defaults=dict(
                ipaddress=parse_ip_address(request),
                useragent=parse_useragent(request),
            )
        )

        if is_vote_created:
            post.increment_vote_count()
            post.author.increment_vote_count()

        return post_vote, is_vote_created


class PostView(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="post_views", db_index=True, null=True, on_delete=models.SET_NULL)
    post = models.ForeignKey(Post, related_name="viewers", db_index=True, on_delete=models.CASCADE)

    ipaddress = models.GenericIPAddressField(null=True)
    useragent = models.CharField(max_length=512, null=True)

    first_view_at = models.DateTimeField(auto_now_add=True)
    registered_view_at = models.DateTimeField(auto_now_add=True)
    last_view_at = models.DateTimeField(auto_now=True)

    unread_comments = models.IntegerField(default=0)

    class Meta:
        db_table = "post_views"
        unique_together = [["user", "post"]]

    @classmethod
    def create_or_update(cls, request, user, post):
        post_view, is_view_created = PostView.objects.get_or_create(
            user=user,
            post=post,
            defaults=dict(
                ipaddress=parse_ip_address(request),
                useragent=parse_useragent(request),
            )
        )

        # increment view counter for ne`w views or for re-opens after cooldown period
        if is_view_created or post_view.registered_view_at < datetime.utcnow() - settings.POST_VIEW_COOLDOWN_PERIOD:
            post_view.registered_view_at = datetime.utcnow()
            post.increment_view_count()

        # reset counters and store last view
        if not is_view_created:
            post_view.unread_comments = 0
            post_view.last_view_at = datetime.utcnow()

        post_view.save()

        return post_view, is_view_created

    @classmethod
    def increment_unread_comments(cls, post):
        PostView.objects.filter(post=post)\
            .update(unread_comments=F("unread_comments") + 1)
