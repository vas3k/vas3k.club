from django.conf import settings
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from bookmarks.models import PostBookmark
from common.pagination import paginate
from posts.helpers import POST_TYPE_ALL, ORDERING_ACTIVITY, sort_feed
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from posts.models.votes import PostVote


@api(require_auth=True)
def md_show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    if not post.can_view(request.me):
        raise Http404()

    post_markdown = f"""# {post.title}\n\n{post.text}"""

    return HttpResponse(post_markdown, content_type="text/plain; charset=utf-8")


@api(require_auth=True)
@require_http_methods(["GET"])
def api_show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if post.type != post_type:
        return redirect("api_show_post", post.type, post.slug)

    if not post.can_view(request.me):
        raise Http404()

    return {
        "post": post.to_dict(including_private=bool(request.me))
    }


@api(require_auth=False)
def json_feed(request, post_type=POST_TYPE_ALL, ordering=ORDERING_ACTIVITY):
    page_number = int(request.GET.get("page") or 1)
    posts = Post.visible_objects()

    # filter posts by type
    if post_type != POST_TYPE_ALL:
        posts = posts.filter(type=post_type)

    # order posts by some metric
    posts = sort_feed(posts, ordering)

    # paginate
    posts = paginate(request, posts)

    return JsonResponse({
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Вастрик Клуб — JSON Feed",
        "home_page_url": settings.APP_HOST,
        "feed_url": f"{settings.APP_HOST}{reverse('json_feed')}",
        "next_url": f"{settings.APP_HOST}{reverse('json_feed')}?page={page_number + 1}",
        "items": [
            post.to_dict(including_private=bool(request.me)) for post in posts
        ]
    }, json_dumps_params=dict(ensure_ascii=False), content_type="application/feed+json")


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def toggle_post_bookmark(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if not post.can_view(request.me):
        raise Http404()

    if request.method == "POST":
        PostBookmark.objects.get_or_create(user=request.me, post=post)
    elif request.method == "DELETE":
        PostBookmark.objects.filter(user=request.me, post=post).delete()

    is_bookmarked = PostBookmark.objects.filter(user=request.me, post=post).exists()

    return {"status": "created" if is_bookmarked else "deleted", "is_bookmarked": is_bookmarked}


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def toggle_post_vote(request, post_slug):
    post = get_object_or_404(Post.objects.select_related("author"), slug=post_slug)

    if not post.can_view(request.me):
        raise Http404()

    if request.method == "POST":
        PostVote.upvote(user=request.me, post=post, request=request)
    elif request.method == "DELETE":
        PostVote.retract_vote(request=request, user=request.me, post=post)

    vote = PostVote.objects.filter(user=request.me, post=post).first()
    post.upvotes = Post.objects.values_list("upvotes", flat=True).get(id=post.id)

    return {
        "post": {"upvotes": post.upvotes},
        "is_voted": vote is not None,
        "upvoted_timestamp": int(vote.created_at.timestamp() * 1000) if vote else 0,
    }


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def toggle_post_subscription(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if not post.can_view(request.me):
        raise Http404()

    if request.method == "POST":
        PostSubscription.objects.get_or_create(user=request.me, post=post)
    elif request.method == "DELETE":
        PostSubscription.unsubscribe(user=request.me, post=post)

    is_subscribed = PostSubscription.get(user=request.me, post=post) is not None

    return {"status": "created" if is_subscribed else "deleted", "is_subscribed": is_subscribed}


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def toggle_post_event_participation(request, post_slug):
    with transaction.atomic():
        posts = Post.objects.select_for_update() if request.method != "GET" else Post.objects
        post = get_object_or_404(posts, slug=post_slug)

        if not post.can_view(request.me):
            raise Http404()

        user_id = str(request.me.id)
        metadata = post.metadata or {}
        event_data = metadata.get("event", {})
        participants = event_data.get("participants", [])
        is_participating = user_id in participants

        if request.method == "POST" and not is_participating:
            participants = [user_id] + participants
            PostSubscription.objects.get_or_create(user=request.me, post=post)
        elif request.method == "DELETE" and is_participating:
            participants = [participant for participant in participants if participant != user_id]
            PostSubscription.unsubscribe(user=request.me, post=post)

        if request.method != "GET":
            event_data["participants"] = participants
            metadata["event"] = event_data
            post.metadata = metadata
            post.save(update_fields=["metadata", "updated_at"])

    is_participating = user_id in participants

    return {"status": "created" if is_participating else "deleted", "is_participating": is_participating}
