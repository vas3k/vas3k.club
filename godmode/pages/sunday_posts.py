from datetime import timedelta, datetime

from django.conf import settings
from django.template.loader import render_to_string

from common.dates import random_date_in_range
from posts.models.post import Post


def sunday_posts(request, admin_page):
    new_posts_cutoff = timedelta(days=200)
    days_range = 15
    posts = []

    while len(posts) < 20:
        random_date_in_the_past = random_date_in_range(settings.LAUNCH_DATE, datetime.utcnow() - new_posts_cutoff)
        top_old_post = Post.visible_objects() \
            .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST]) \
            .filter(moderation_status=Post.MODERATION_APPROVED) \
            .filter(
                published_at__gte=random_date_in_the_past,
                published_at__lte=random_date_in_the_past + timedelta(days=days_range)
            ) \
            .order_by("-upvotes") \
            .first()

        if top_old_post:
            posts.append(top_old_post)

    return render_to_string("godmode/pages/posts.html", {
        "posts": posts
    }, request=request)

