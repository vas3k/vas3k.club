from datetime import date, timedelta, datetime

import requests
from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import render, get_object_or_404

from comments.models import Comment
from landing.models import GodSettings
from posts.models import Post
from users.models import User


def email_confirm(request, user_id, secret):
    user = get_object_or_404(User, id=user_id, secret_hash=secret)

    user.is_email_verified = True
    user.save()

    return render(request, "message.html", {
        "title": "💌 Ваш адрес почты подтвержден",
        "message": "Теперь туда будет приходить еженедельный журнал Клуба и другие оповещалки."
    })


def email_unsubscribe(request, user_id, secret):
    user = get_object_or_404(User, id=user_id, secret_hash=secret)

    user.is_email_unsubscribed = True
    user.email_digest_type = User.EMAIL_DIGEST_TYPE_NOPE
    user.save()

    return render(request, "message.html", {
        "title": "🙅‍♀️ Вы отписались от всех писем Клуба",
        "message": "Мы ценим ваше время, потому отписали вас от всего и полностью. "
                   "Вы больше не получите от нас никаких писем. "
                   "Если захотите подписаться заново — напишите нам в поддержку."
    })


def daily_digest(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=1)

    created_at_condition = dict(created_at__gte=start_date - timedelta(days=1000), created_at__lte=end_date)
    published_at_condition = dict(published_at__gte=start_date - timedelta(days=1000), published_at__lte=end_date)

    # Moon
    moon_phase_raw = requests.get(
        "https://simplescraper.io/api/y4gLaoFV8m9cnOMXk4JB?apikey=D5UTz8BLaGP8x5ZM8n8553AFqRYiH7QD&offset=0&limit=20"
    ).json()
    moon_phase = {
        "club_day": (datetime.utcnow() - settings.LAUNCH_DATE).days,
        "phase_num": [mp["moon_phase"] for mp in moon_phase_raw["data"] if mp["index"] == 1][0],
        "phase_sign": [mp["moon_phase"] for mp in moon_phase_raw["data"] if mp["index"] == 2][0],
        "phase_description": [mp["moon_description"] for mp in moon_phase_raw["data"] if mp["index"] == 11][0][:-18],
    }

    # Best posts
    posts = Post.visible_objects()\
        .filter(is_approved_by_moderator=True, **published_at_condition)\
        .exclude(type__in=[Post.TYPE_WEEKLY_DIGEST])\
        .order_by("-upvotes")[:100]

    # Best comments
    comments = Comment.visible_objects() \
        .filter(**created_at_condition) \
        .filter(is_deleted=False)\
        .order_by("-upvotes")[:1]

    # New joiners
    intros = Post.visible_objects()\
        .filter(type=Post.TYPE_INTRO, **published_at_condition)\
        .order_by("-upvotes")

    return render(request, "emails/daily.html", {
        "user": user,
        "intros": intros,
        "posts": posts,
        "comments": comments,
        "date": end_date,
        "moon_phase": moon_phase,
    })


def weekly_digest(request):
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=8)  # make 8, not 7, to include marginal users

    created_at_condition = dict(created_at__gte=start_date, created_at__lte=end_date)
    published_at_condition = dict(published_at__gte=start_date, published_at__lte=end_date)

    # New users
    intros = Post.visible_objects()\
        .filter(type=Post.TYPE_INTRO, **published_at_condition)\
        .order_by("-upvotes")
    newbie_count = User.objects\
        .filter(is_profile_reviewed=True, **created_at_condition)\
        .count()

    # Best posts
    featured_post = Post.visible_objects()\
        .exclude(type=Post.TYPE_INTRO)\
        .filter(
            label__isnull=False,
            label__code="top_week",
            **published_at_condition
         )\
        .order_by("-upvotes")\
        .first()

    posts = Post.visible_objects()\
        .filter(is_approved_by_moderator=True, **published_at_condition)\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
        .exclude(id=featured_post.id if featured_post else None)\
        .order_by("-upvotes")[:12]

    # Video of the week
    top_video_comment = Comment.visible_objects() \
        .filter(**created_at_condition) \
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
        .exclude(id=top_video_comment.id if top_video_comment else None)\
        .order_by("-upvotes")[:3]

    # Intro from author
    author_intro = GodSettings.objects.first().digest_intro

    if not author_intro and not posts and not comments:
        raise Http404()

    return render(request, "emails/weekly_digest.html", {
        "posts": posts,
        "comments": comments,
        "intros": intros,
        "newbie_count": newbie_count,
        "top_video_comment": top_video_comment,
        "top_video_post": top_video_post,
        "featured_post": featured_post,
        "author_intro": author_intro,
        "issue_number": (start_date - settings.LAUNCH_DATE).days // 7 + 1
    })
