from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Count, Q
from django.template.loader import render_to_string
from django.urls import reverse

from badges.models import UserBadge
from club.exceptions import NotFound
from comments.models import Comment, CommentVote
from common.flat_earth import parse_horoscope
from landing.models import GodSettings
from posts.models.post import Post
from posts.models.votes import PostVote
from users.models.achievements import UserAchievement
from users.models.user import User


def generate_daily_digest(user):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)
    if end_date.weekday() == 1:
        # we don't have daily on sundays and mondays, we need to include all these posts at tuesday
        start_date = end_date - timedelta(days=3)

    if settings.DEBUG:
        start_date = end_date - timedelta(days=1000)

    created_at_condition = dict(created_at__gte=start_date, created_at__lte=end_date)
    published_at_condition = dict(published_at__gte=start_date, published_at__lte=end_date)

    # Moon
    moon_phase = parse_horoscope()

    # New actions
    subscription_comments = Comment.visible_objects()\
        .filter(
            post__subscriptions__user=user,
            **created_at_condition
        )\
        .values("post__type", "post__slug", "post__title", "post__author_id")\
        .annotate(count=Count("id"))\
        .order_by()

    replies = Comment.visible_objects()\
        .filter(
            reply_to__author=user,
            **created_at_condition
        )\
        .values("post__type", "post__slug", "post__title")\
        .annotate(count=Count("reply_to_id"))\
        .order_by()

    new_events = [
        {
            "type": "my_post_comment",
            "post_url": reverse("show_post", kwargs={"post_type": e["post__type"], "post_slug": e["post__slug"]}),
            "post_title": e["post__title"],
            "count": e["count"],
        } for e in subscription_comments if e["post__author_id"] == user.id
    ] + [
        {
            "type": "subscribed_post_comment",
            "post_url": reverse("show_post", kwargs={"post_type": e["post__type"], "post_slug": e["post__slug"]}),
            "post_title": e["post__title"],
            "count": e["count"],
        } for e in subscription_comments if e["post__author_id"] != user.id
    ] + [
        {
            "type": "reply",
            "post_url": reverse("show_post", kwargs={"post_type": e["post__type"], "post_slug": e["post__slug"]}),
            "post_title": e["post__title"],
            "count": e["count"],
        } for e in replies
    ]

    upvotes = PostVote.objects.filter(post__author=user, **created_at_condition).count() \
        + CommentVote.objects.filter(comment__author=user, **created_at_condition).count()

    if upvotes:
        new_events = [
            {
                "type": "upvotes",
                "count": upvotes,
            }
        ] + new_events

    # Mentions
    mentions = Comment.visible_objects() \
        .filter(**created_at_condition) \
        .filter(text__regex=fr"@\y{user.slug}\y", is_deleted=False)\
        .exclude(reply_to__author=user)\
        .order_by("-upvotes")[:5]

    # Best posts
    posts = Post.visible_objects()\
        .filter(**published_at_condition)\
        .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES))\
        .filter(is_visible_in_feeds=True)\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .exclude(is_shadow_banned=True)\
        .order_by("-upvotes")[:100]

    # New joiners
    intros = Post.visible_objects()\
        .filter(type=Post.TYPE_INTRO, **published_at_condition)\
        .order_by("-upvotes")

    if not posts and not mentions and not intros:
        raise NotFound()

    og_params = urlencode({
        **settings.OG_IMAGE_GENERATOR_DEFAULTS,
        "title": f"Ежедневный дайджест пользователя {user.slug}",
        "author": "THE MACHINE",
        "ava": settings.OG_MACHINE_AUTHOR_LOGO
    })

    return render_to_string("emails/daily.html", {
        "user": user,
        "events": new_events,
        "intros": intros,
        "posts": posts,
        "mentions": mentions,
        "date": end_date,
        "moon_phase": moon_phase,
        "og_image_url": f"{settings.OG_IMAGE_GENERATOR_URL}?{og_params}"
    })


def generate_weekly_digest(no_footer=False):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=8)

    if settings.DEBUG:
        start_date = end_date - timedelta(days=1000)

    created_at_condition = dict(created_at__gte=start_date, created_at__lte=end_date)
    published_at_condition = dict(published_at__gte=start_date, published_at__lte=end_date)

    # New users
    intros = Post.visible_objects()\
        .filter(type=Post.TYPE_INTRO, **published_at_condition)\
        .order_by("-upvotes")

    newbie_count = User.objects\
        .filter(
            moderation_status=User.MODERATION_STATUS_APPROVED,
            **created_at_condition
        )\
        .count()

    # Best posts
    featured_post = Post.visible_objects()\
        .exclude(type=Post.TYPE_INTRO)\
        .filter(
            label_code__isnull=False,
            label_code="top_week",
            **published_at_condition
         )\
        .order_by("-upvotes")\
        .first()

    posts = Post.visible_objects()\
        .filter(**published_at_condition)\
        .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES))\
        .filter(is_visible_in_feeds=True)\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .exclude(id=featured_post.id if featured_post else None)\
        .exclude(label_code__isnull=False, label_code="ad")\
        .exclude(is_shadow_banned=True)\
        .order_by("-upvotes")

    post_count = posts.count()
    posts = posts[:12]

    # Video of the week
    top_video_comment = Comment.visible_objects()\
        .filter(**created_at_condition)\
        .filter(is_deleted=False)\
        .filter(upvotes__gte=3)\
        .filter(Q(text__contains="https://youtu.be/") | Q(text__contains="youtube.com/watch"))\
        .order_by("-upvotes")\
        .first()

    top_video_post = None
    if not top_video_comment:
        top_video_post = Post.visible_objects() \
            .filter(type=Post.TYPE_LINK, upvotes__gte=3) \
            .filter(**published_at_condition) \
            .filter(Q(url__contains="https://youtu.be/") | Q(url__contains="youtube.com/watch")) \
            .order_by("-upvotes") \
            .first()

    # Best comments
    comments = Comment.visible_objects() \
        .filter(**created_at_condition) \
        .filter(is_deleted=False)\
        .exclude(post__type=Post.TYPE_BATTLE)\
        .exclude(post__is_visible=False)\
        .exclude(post__is_visible_in_feeds=False)\
        .exclude(id=top_video_comment.id if top_video_comment else None)\
        .order_by("-upvotes")[:3]

    # Get intro and title
    god_settings = GodSettings.objects.first()
    digest_title = god_settings.digest_title
    digest_intro = god_settings.digest_intro

    if not digest_intro and not posts and not comments:
        raise NotFound()

    # New achievements
    achievements = UserAchievement.objects\
        .filter(**created_at_condition)\
        .select_related("user", "achievement")\
        .order_by("achievement")  # required for grouping

    # New badges
    badges = UserBadge.objects\
        .select_related("badge", "to_user")\
        .filter(**created_at_condition)\
        .order_by('-created_at')[:10]

    issue_number = (end_date - settings.LAUNCH_DATE).days // 7

    og_params = urlencode({
        **settings.OG_IMAGE_GENERATOR_DEFAULTS,
        "title": f"Клубный журнал. Итоги недели. Выпуск #{issue_number}.",
        "author": "THE MACHINE",
        "ava": settings.OG_MACHINE_AUTHOR_LOGO
    })

    return render_to_string("emails/weekly.html", {
        "posts": posts,
        "comments": comments,
        "intros": intros,
        "achievements": achievements,
        "badges": badges,
        "newbie_count": newbie_count,
        "post_count": post_count,
        "top_video_comment": top_video_comment,
        "top_video_post": top_video_post,
        "featured_post": featured_post,
        "digest_title": digest_title,
        "digest_intro": digest_intro,
        "issue_number": issue_number,
        "is_footer_excluded": no_footer,
        "og_image_url": f"{settings.OG_IMAGE_GENERATOR_URL}?{og_params}"
    })
