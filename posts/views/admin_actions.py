from datetime import datetime, timedelta

from django.shortcuts import get_object_or_404, render, redirect

from authn.decorators.auth import require_auth, require_moderator_role, require_curator_role
from club.exceptions import AccessDenied
from comments.models import Comment
from common.data.labels import LABELS
from notifications.telegram.common import render_html_message
from notifications.telegram.posts import announce_in_club_channel, notify_post_collectible_tag_owners
from posts.forms.admin import PostAdminForm, PostAnnounceForm, PostCuratorForm
from posts.helpers import extract_any_image
from posts.models.linked import LinkedPost
from posts.models.post import Post
from users.models.user import User


@require_auth
@require_curator_role
def curate_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if request.method == "POST":
        form = PostCuratorForm(request.POST)
        if form.is_valid():
            return do_post_curator_actions(request, post, form.cleaned_data)
    else:
        form = PostCuratorForm()

    return render(request, "admin/simple_form.html", {
        "title": "Курирование поста",
        "post": post,
        "form": form
    })


@require_auth
@require_moderator_role
def admin_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if request.method == "POST":
        form = PostAdminForm(request.POST)
        if form.is_valid():
            return do_post_admin_actions(request, post, form.cleaned_data)
    else:
        form = PostAdminForm()

    return render(request, "admin/simple_form.html", {
        "title": "Админить пост",
        "post": post,
        "form": form
    })


@require_auth
@require_moderator_role
def announce_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    initial = {
        "text": render_html_message("channel_post_announce.html", post=post),
        "image": extract_any_image(post),
    }

    if request.method == "POST":
        form = PostAnnounceForm(request.POST, initial=initial)
        if form.is_valid():
            announce_in_club_channel(
                post=post,
                announce_text=form.cleaned_data["text"],
                image=form.cleaned_data["image"] if form.cleaned_data["with_image"] else None
            )
            return render(request, "message.html", {
                "title": "Запощено ✅"
            })
    else:
        form = PostAnnounceForm(initial=initial)

    return render(request, "admin/simple_form.html", {
        "title": "Анонсировать пост на канале",
        "post": post,
        "form": form
    })


def do_post_admin_actions(request, post, data):
    if not request.me.is_moderator:
        raise AccessDenied()

    do_common_admin_and_curator_actions(request, post, data)

    # Close comments
    if data["toggle_is_commentable"]:
        post.is_commentable = not post.is_commentable
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

    # Show back in feeds
    if data["show_in_feeds"]:
        post.is_visible_in_feeds = True
        post.save()

    # Ping collectible tag owners again
    if data["re_ping_collectible_tag_owners"]:
        if post.collectible_tag_code:
            notify_post_collectible_tag_owners(post)
