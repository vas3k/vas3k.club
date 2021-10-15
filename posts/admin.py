from datetime import datetime, timedelta

from django.shortcuts import redirect

from club.exceptions import AccessDenied
from comments.models import Comment
from common.data.labels import LABELS
from posts.models.linked import LinkedPost
from users.models.user import User


def do_post_admin_actions(request, post, data):
    if not request.me.is_moderator:
        raise AccessDenied()

    do_common_admin_and_curator_actions(request, post, data)

    # Close comments
    if data["close_comments"]:
        post.is_commentable = False
        post.save()

    # Transfer ownership to the given username
    if data["transfer_ownership"]:
        user = User.objects.filter(slug=data["transfer_ownership"].strip()).first()
        if user:
            post.author = user
            post.save()

    if data["refresh_linked"]:
        LinkedPost.create_links_from_text(post, post.text)
        post_comments = Comment.visible_objects().filter(post=post, is_deleted=False)
        for comment in post_comments:
            LinkedPost.create_links_from_text(comment.post, comment.text)

    return redirect("show_post", post.type, post.slug)


def do_post_curator_actions(request, post, data):
    if not request.me.is_curator:
        raise AccessDenied()

    do_common_admin_and_curator_actions(request, post, data)

    return redirect("show_post", post.type, post.slug)


def do_common_admin_and_curator_actions(request, post, data):
    # Change type
    if data["change_type"]:
        post.type = data["change_type"]
        post.save()

    # Labels
    if data["new_label"]:
        label = LABELS.get(data["new_label"])
        if label:
            post.label_code = data["new_label"]
            post.save()

    if data["remove_label"]:
        post.label_code = None
        post.save()

    # Pins
    if data["add_pin"]:
        post.is_pinned_until = datetime.utcnow() + timedelta(days=data["pin_days"])
        post.save()

    if data["remove_pin"]:
        post.is_pinned_until = None
        post.save()

    # Moving up
    if data["move_up"]:
        post.last_activity_at = datetime.utcnow()
        post.save()

    # Moving down
    if data["move_down"]:
        post.last_activity_at -= timedelta(days=3)
        post.save()

    # Shadow banning
    if data["shadow_ban"]:
        post.is_shadow_banned = True
        post.save()

    # Hide from feeds
    if data["hide_from_feeds"]:
        post.is_visible_in_feeds = False
        post.save()
