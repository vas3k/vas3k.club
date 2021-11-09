from datetime import datetime, timedelta

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from auth.helpers import auth_required
from club import features
from common.feature_flags import feature_switch, noop
from common.pagination import paginate
from posts.models.post import Post
from posts.models.topics import Topic

POST_TYPE_ALL = "all"

ORDERING_ACTIVITY = "activity"
ORDERING_NEW = "new"
ORDERING_HOT = "hot"
ORDERING_TOP = "top"
ORDERING_TOP_WEEK = "top_week"
ORDERING_TOP_MONTH = "top_month"


@feature_switch(features.PRIVATE_FEED, yes=auth_required, no=noop)
def feed(request, post_type=POST_TYPE_ALL, topic_slug=None, label_code=None, ordering=ORDERING_ACTIVITY):
    post_type = post_type or Post

    if request.me:
        request.me.update_last_activity()
        posts = Post.objects_for_user(request.me)
    else:
        posts = Post.visible_objects()

    # filter posts by type
    if post_type != POST_TYPE_ALL:
        posts = posts.filter(type=post_type)

    # filter by topic
    topic = None
    if topic_slug:
        topic = get_object_or_404(Topic, slug=topic_slug)
        posts = posts.filter(topic=topic)

    # filter by label
    if label_code:
        posts = posts.filter(label_code=label_code)

    # hide non-public posts and intros from unauthorized users
    if not request.me:
        posts = posts.exclude(is_public=False).exclude(type=Post.TYPE_INTRO)

    # exclude shadow banned posts, but show them in "new" tab
    if ordering != ORDERING_NEW:
        if request.me:
            posts = posts.exclude(Q(is_shadow_banned=True) & ~Q(author_id=request.me.id))
        else:
            posts = posts.exclude(is_shadow_banned=True)

    # hide no-feed posts (show only inside rooms and topics)
    if not topic and not label_code:
        posts = posts.filter(is_visible_in_feeds=True)

    # order posts by some metric
    if ordering:
        if ordering == ORDERING_ACTIVITY:
            posts = posts.order_by("-last_activity_at")
        elif ordering == ORDERING_NEW:
            posts = posts.order_by("-published_at", "-created_at")
        elif ordering == ORDERING_TOP:
            posts = posts.order_by("-upvotes")
        elif ordering == ORDERING_HOT:
            posts = posts.order_by("-hotness")
        elif ordering == ORDERING_TOP_WEEK:
            posts = posts.filter(
                published_at__gte=datetime.utcnow() - timedelta(days=7)
            ).order_by("-upvotes")
        elif ordering == ORDERING_TOP_MONTH:
            posts = posts.filter(
                published_at__gte=datetime.utcnow() - timedelta(days=31)
            ).order_by("-upvotes")
        else:
            raise Http404()

    # split results into pinned and unpinned posts on main page
    pinned_posts = []
    if ordering == ORDERING_ACTIVITY:
        pinned_posts = posts.filter(is_pinned_until__gte=datetime.utcnow())
        posts = posts.exclude(id__in=[p.id for p in pinned_posts])

    return render(request, "feed.html", {
        "post_type": post_type or POST_TYPE_ALL,
        "ordering": ordering,
        "topic": topic,
        "label_code": label_code,
        "posts": paginate(request, posts),
        "pinned_posts": pinned_posts,
        "date_month_ago": datetime.utcnow() - timedelta(days=30),
    })
