from datetime import datetime, timedelta

from django.shortcuts import render

from authn.decorators.auth import require_auth
from posts.models.post import Post


@require_auth
def event_calendar(request):
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    posts = Post.objects_for_user(request.me)\
        .filter(type=Post.TYPE_EVENT, published_at__gte=today - timedelta(days=365))\
        .exclude(author__muted_to__user_from=request.me)

    events = []
    for post in posts:
        if not post.metadata or not post.metadata.get("event"):
            continue

        try:
            event_at = post.event_datetime
        except (TypeError, ValueError, KeyError):
            continue

        if event_at >= today:
            events.append(post)

    events.sort(key=lambda post: post.event_datetime)

    return render(request, "posts/items/calendar.html", {
        "post_type": "calendar",
        "posts": events,
    })
