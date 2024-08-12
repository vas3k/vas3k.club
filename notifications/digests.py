import base64
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode

from django.conf import settings
from django.db.models import Count, Q
from django.template.loader import render_to_string

from badges.models import UserBadge
from club.exceptions import NotFound
from comments.models import Comment, CommentVote
from common.data.greetings import DUMB_GREETINGS
from landing.models import GodSettings
from misc.models import ProTip
from posts.models.post import Post
from posts.models.votes import PostVote
from users.models.achievements import UserAchievement
from users.models.user import User


BONUS_HOURS = 10  # for better/honest rating estimation of "night" posts
MIN_TOP_POST_UPVOTES = 30


def generate_daily_digest(user):
    end_date = datetime.utcnow()

    if end_date.weekday() == 1:
        # we don't have daily digest on weekends and mondays, we need to include all these posts at tuesday
        start_date = end_date - timedelta(hours=3 * 24 + BONUS_HOURS)
    else:
        # other days are quieter
        start_date = end_date - timedelta(hours=2 * 24 + BONUS_HOURS)

    if settings.DEBUG:
        start_date = end_date - timedelta(days=1000)

    created_at_condition = dict(created_at__gte=start_date, created_at__lte=end_date)
    published_at_condition = dict(published_at__gte=start_date, published_at__lte=end_date)

    # New comments
    new_post_comments = Comment.visible_objects()\
        .filter(
            post__author=user,
            **created_at_condition
        )\
        .values("post__type", "post__slug", "post__title", "post__author_id")\
        .annotate(count=Count("post"))\
        .order_by("-count")\
        .first()

    new_upvotes = PostVote.objects.filter(post__author=user, **created_at_condition).count() \
        + CommentVote.objects.filter(comment__author=user, **created_at_condition).count()

    # New posts
    new_posts = Post.visible_objects()\
        .filter(**published_at_condition)\
        .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES))\
        .filter(is_visible_in_feeds=True)\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .exclude(is_shadow_banned=True)\
        .order_by("-upvotes")[:3]

    # Hot posts
    hot_posts = Post.visible_objects()\
        .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES))\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST]) \
        .exclude(id__in=[p.id for p in new_posts]) \
        .order_by("-hotness")[:3]

    # New intros
    intros = Post.visible_objects()\
        .filter(type=Post.TYPE_INTRO, **published_at_condition)\
        .order_by("-upvotes")[:3]

    # Top post 1 year ago
    top_old_post = Post.visible_objects()\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES))\
        .filter(
            published_at__gte=start_date - timedelta(days=365),
            published_at__lte=end_date - timedelta(days=364)
         )\
        .order_by("-upvotes")\
        .first()

    # Filter out "bad" top posts
    if top_old_post.upvotes < MIN_TOP_POST_UPVOTES:
        top_old_post = None

    if not new_post_comments and not new_posts and not intros:
        raise NotFound()

    return render_to_string("messages/good_morning.html", {
        "user": user,
        "intros": intros,
        "new_posts": new_posts,
        "hot_posts": hot_posts,
        "top_old_post": top_old_post,
        "stats": {
            "new_post_comments": new_post_comments,
            "new_upvotes": new_upvotes,
        },
        "settings": settings,  # why not automatically?
        "date": end_date,
        "greetings": random.choice(DUMB_GREETINGS),
        "secret_code": base64.b64encode(user.secret_hash.encode("utf-8")).decode()
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
        .filter(post__is_approved_by_moderator=True)\
        .filter(upvotes__gte=3)\
        .filter(Q(text__contains="https://youtu.be/") | Q(text__contains="youtube.com/watch"))\
        .order_by("-upvotes")\
        .first()

    top_video_post = None
    if not top_video_comment:
        top_video_post = Post.visible_objects() \
            .filter(type=Post.TYPE_LINK, upvotes__gte=3) \
            .filter(post__is_approved_by_moderator=True) \
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
        .exclude(post__is_approved_by_moderator=False)\
        .exclude(post__is_visible_in_feeds=False)\
        .exclude(id=top_video_comment.id if top_video_comment else None)\
        .order_by("-upvotes")[:3]

    # Best post 1 year ago
    top_old_post = Post.visible_objects()\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES))\
        .filter(
            published_at__gte=start_date - timedelta(days=365),
            published_at__lte=end_date - timedelta(days=365)
         )\
        .order_by("-upvotes")\
        .first()

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

    # Pro tips
    pro_tip = ProTip.weekly_tip(issue_number)

    og_params = urlencode({
        **settings.OG_IMAGE_GENERATOR_DEFAULTS,
        "title": f"Клубный журнал. Итоги недели. Выпуск #{issue_number}.",
        "author": "THE MACHINE",
        "ava": settings.OG_MACHINE_AUTHOR_LOGO
    })

    og_description = render_to_string("emails/weekly_og_description.html", {
        "newbie_count": newbie_count,
        "post_count": post_count,
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
        "top_old_post": top_old_post,
        "featured_post": featured_post,
        "digest_title": digest_title,
        "digest_intro": digest_intro,
        "issue_number": issue_number,
        "pro_tip": pro_tip,
        "is_footer_excluded": no_footer,
        "og_image_url": f"{settings.OG_IMAGE_GENERATOR_URL}?{og_params}",
        "og_description": og_description,
    }), og_description
