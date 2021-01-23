from django.shortcuts import get_object_or_404, render

from auth.helpers import auth_required, moderator_role_required
from notifications.telegram.common import render_html_message
from notifications.telegram.posts import announce_in_club_channel
from posts.admin import do_post_admin_actions
from posts.forms.admin import PostAdminForm, PostAnnounceForm
from posts.helpers import extract_any_image
from posts.models.post import Post


@auth_required
@moderator_role_required
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


@auth_required
@moderator_role_required
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
