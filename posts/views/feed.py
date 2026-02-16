from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404, render

from authn.decorators.auth import require_auth
from club import features
from common.feature_flags import feature_switch, noop
from common.pagination import paginate
from posts.helpers import POST_TYPE_ALL, ORDERING_ACTIVITY, get_feed_posts
from posts.models.post import Post
from rooms.models import Room


@feature_switch(features.PRIVATE_FEED, yes=require_auth, no=noop)
def feed(
    request,
    post_type=POST_TYPE_ALL,
    room_slug=None,
    label_code=None,
    ordering=ORDERING_ACTIVITY,
    ordering_param=None
):
    if request.me:
        request.me.update_last_activity()

    # resolve room slug to room object
    room = get_object_or_404(Room, slug=room_slug) if room_slug else None

    # get filtered and sorted posts
    posts = get_feed_posts(
        user=request.me,
        post_type=post_type,
        room=room,
        label_code=label_code,
        ordering=ordering,
        ordering_param=ordering_param,
    )

    # for main page — add pinned posts
    pinned_posts = []
    if ordering == ORDERING_ACTIVITY:
        pinned_posts = posts.filter(is_pinned_until__gte=datetime.utcnow())
        posts = posts.exclude(id__in=[p.id for p in pinned_posts])

    # for moderators — pending posts
    waiting_for_moderation_posts = []
    if request.me and request.me.is_moderator and ordering == ORDERING_ACTIVITY:
        waiting_for_moderation_posts = Post.visible_objects()\
            .filter(moderation_status=Post.MODERATION_PENDING)\
            .exclude(author=request.me)

    return render(request, "feed.html", {
        "post_type": post_type or POST_TYPE_ALL,
        "ordering": ordering,
        "ordering_full": ordering + (f":{ordering_param}" if ordering_param else ""),
        "room": room,
        "label_code": label_code,
        "posts": paginate(request, posts),
        "pinned_posts": pinned_posts,
        "waiting_for_moderation_posts": waiting_for_moderation_posts,
        "date_month_ago": datetime.utcnow() - timedelta(days=30),
    })
