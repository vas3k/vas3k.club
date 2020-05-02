from datetime import datetime, timedelta

from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from auth.helpers import auth_required
from common.pagination import paginate
from posts.models import Post, Topic


@auth_required
def feed(request, post_type=None, topic_slug=None, ordering="activity"):
    if request.me:
        request.me.update_last_activity()
        posts = Post.objects_for_user(request.me)
    else:
        posts = Post.visible_objects()

    # filter posts by type
    if post_type:
        posts = posts.filter(type=post_type)

    # filter by topic
    topic = None
    if topic_slug:
        topic = get_object_or_404(Topic, slug=topic_slug)
        posts = posts.filter(topic=topic)

    # hide non-public posts and intros from unauthorized users
    if not request.me:
        posts = posts.exclude(is_public=False).exclude(type=Post.TYPE_INTRO)

    # exclude shadow banned posts
    if request.me:
        posts = posts.exclude(Q(is_shadow_banned=True) & ~Q(author_id=request.me.id))

    # no type and topic? probably it's the main page, let's apply some more filters
    if not topic and not post_type:
        posts = posts.filter(is_visible_on_main_page=True)

    # order posts by some metric
    if ordering:
        if ordering == "activity":
            posts = posts.order_by("-last_activity_at")
        elif ordering == "new":
            posts = posts.order_by("-published_at")
        elif ordering == "top":
            posts = posts.filter(
                published_at__gte=datetime.utcnow() - timedelta(days=60)
            ).order_by("upvotes")
        else:
            raise Http404()

    # split results into pinned and unpinned posts
    pinned_posts = posts.filter(is_pinned_until__gte=datetime.utcnow())
    posts = posts.exclude(id__in=[p.id for p in pinned_posts])

    return render(request, "posts/feed.html", {
        "posts": paginate(request, posts),
        "pinned_posts": pinned_posts,
        "post_type": post_type,
        "ordering": ordering,
        "topic": topic,
    })
