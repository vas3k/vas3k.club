from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from posts.models.post import Post
from bookmarks.models import PostBookmark
from posts.models.subscriptions import PostSubscription
from posts.models.votes import PostVote


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_post_bookmark(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    bookmark, is_created = PostBookmark.objects.get_or_create(
        user=request.me,
        post=post,
    )

    if not is_created:
        bookmark.delete()

    return {
        "status": "created" if is_created else "deleted"
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def upvote_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    post_vote, is_vote_created = PostVote.upvote(
        user=request.me,
        post=post,
        request=request,
    )

    return {
        "post": {
            "upvotes": post.upvotes + (1 if is_vote_created else 0),
        },
        "upvoted_timestamp": int(post_vote.created_at.timestamp() * 1000) if post_vote else 0
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def retract_post_vote(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    is_retracted = PostVote.retract_vote(
        request=request,
        user=request.me,
        post=post,
    )

    return {
        "success": is_retracted,
        "post": {
            "upvotes": post.upvotes - (1 if is_retracted else 0)
        }
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_post_subscription(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    subscription, is_created = PostSubscription.subscribe(
        user=request.me,
        post=post,
        type=PostSubscription.TYPE_TOP_LEVEL_ONLY,
    )

    if not is_created:
        # already exist? remove it
        PostSubscription.unsubscribe(
            user=request.me,
            post=post,
        )

    return {
        "status": "created" if is_created else "deleted"
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_post_event_participation(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    user_id = str(request.me.id)
    is_created = False

    with transaction.atomic():
        metadata = post.metadata or {}
        event_data = metadata.get("event", {})
        participants = event_data.get("participants", [])

        if user_id not in participants:
            # Add participant to the beginning of the list
            participants = [user_id] + participants

            # Ensure uniqueness
            participants = list(set(participants))

            PostSubscription.subscribe(
                user=request.me,
                post=post,
                type=PostSubscription.TYPE_TOP_LEVEL_ONLY,
            )

            is_created = True
        else:
            # Remove participant
            participants = [pid for pid in participants if pid != user_id]

            PostSubscription.unsubscribe(
                user=request.me,
                post=post,
            )

        # Update metadata safely
        event_data["participants"] = participants
        metadata["event"] = event_data
        post.metadata = metadata
        post.save(update_fields=["metadata", "updated_at"])

    return {
        "status": "created" if is_created else "deleted"
    }
