from datetime import datetime, timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from authn.decorators.auth import require_auth
from club import features
from common.feature_flags import feature_switch, noop
from common.pagination import paginate
from posts.helpers import POST_TYPE_ALL, ORDERING_ACTIVITY, ORDERING_NEW, sort_feed, ORDERING_HOT
from posts.models.post import Post
from rooms.models import Room, RoomMuted
from users.models.mute import UserMuted


@feature_switch(features.PRIVATE_FEED, yes=require_auth, no=noop)
def feed(request, post_type=POST_TYPE_ALL, room_slug=None, label_code=None, ordering=ORDERING_ACTIVITY):
    post_type = post_type or Post

    if request.me:
        request.me.update_last_activity()
        posts = Post.objects_for_user(request.me)
    else:
        posts = Post.visible_objects()

    # filter posts by type
    if post_type != POST_TYPE_ALL:
        posts = posts.filter(type=post_type)

    # filter by room
    if room_slug:
        room = get_object_or_404(Room, slug=room_slug)
        posts = posts.filter(room=room)
    else:
        room = None

    # filter by label
    if label_code:
        posts = posts.filter(label_code=label_code)

    # hide muted users and rooms
    if request.me:
        # exclude muted users
        posts = posts.exclude(author__muted_to__user_from=request.me)

        # exclude muted rooms (only if not in the room)
        if not room and ordering in [ORDERING_NEW, ORDERING_HOT, ORDERING_ACTIVITY]:
            posts = posts.exclude(room__muted_users__user=request.me)

        # TODO: old code, let's check what works faster
        # TODO: REMOVE IT in 2025 if no performance degradation detected
        # muted_rooms = RoomMuted.muted_by_user(user=request.me).values_list("room_id").all()
        # if muted_rooms:
        #     posts = posts.exclude(room_id__in=muted_rooms)
        #
        # muted_users = UserMuted.objects.filter(user_from=request.me).values_list("user_to_id").all()
        # if muted_users:
        #     posts = posts.exclude(author_id__in=muted_users)

    # hide non-public posts and intros from unauthorized users
    if not request.me:
        posts = posts.exclude(is_public=False).exclude(type=Post.TYPE_INTRO)

    # exclude shadow-banned posts from main feed, but show them in "new" tab
    if ordering != ORDERING_NEW:
        if request.me:
            posts = posts.exclude(Q(is_shadow_banned=True) & ~Q(author_id=request.me.id))
        else:
            posts = posts.exclude(is_shadow_banned=True)

    # hide no-feed posts (show only inside rooms and topics)
    if not room and not label_code:
        posts = posts.filter(is_visible_in_feeds=True)

    # order posts by some metric
    posts = sort_feed(posts, ordering)

    # for main page — add pinned posts
    pinned_posts = []
    if ordering == ORDERING_ACTIVITY:
        pinned_posts = posts.filter(is_pinned_until__gte=datetime.utcnow())
        posts = posts.exclude(id__in=[p.id for p in pinned_posts])

    return render(request, "feed.html", {
        "post_type": post_type or POST_TYPE_ALL,
        "ordering": ordering,
        "room": room,
        "label_code": label_code,
        "posts": paginate(request, posts),
        "pinned_posts": pinned_posts,
        "date_month_ago": datetime.utcnow() - timedelta(days=30),
    })
