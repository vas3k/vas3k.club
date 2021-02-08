from datetime import datetime, timedelta

from django.shortcuts import redirect

from club.exceptions import AccessDenied
from common.data.labels import LABELS
from users.models.user import User


def do_post_admin_actions(request, post, data):
    if not request.me.is_moderator:
        raise AccessDenied()

    # Change type
    if data["change_type"]:
        post.type = data["change_type"]
        post.save()

    # Labels
    if data["new_label"]:
        label = LABELS.get(data["new_label"])
        if label:
            post.label = {"code": data["new_label"], **label}
            post.save()

    if data["remove_label"]:
        post.label = None
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

    # Shadow banning
    if data["shadow_ban"]:
        post.is_shadow_banned = True
        post.save()

    # Hide from main page
    if data["hide_on_main"]:
        post.is_visible_on_main_page = False
        post.save()

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

    return redirect("show_post", post.type, post.slug)
