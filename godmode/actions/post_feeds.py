from datetime import datetime, timedelta

from django import forms
from django.shortcuts import render

from comments.models import Comment
from notifications.telegram.posts import notify_post_collectible_tag_owners
from posts.models.linked import LinkedPost
from posts.models.post import Post


class PostFeedsForm(forms.Form):
    move_up = forms.BooleanField(
        label="Подбросить на главной",
        required=False
    )

    move_down = forms.BooleanField(
        label="Опустить на главной",
        required=False
    )

    re_ping_collectible_tag_owners = forms.BooleanField(
        label="Перепингануть подписчиков коллективного тега",
        required=False,
    )

    refresh_linked = forms.BooleanField(
        label="Обновить связанные посты",
        required=False,
    )



def get_feeds_action(request, post: Post, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": post,
        "form": PostFeedsForm(),
    })


def post_feeds_action(request, post: Post, **context):
    form = PostFeedsForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Moving up
        if data["move_up"]:
            post.last_activity_at = datetime.utcnow()
            post.save()

        # Moving down
        if data["move_down"]:
            post.last_activity_at -= timedelta(days=3)
            post.save()

        # Ping collectible tag owners again
        if data["re_ping_collectible_tag_owners"]:
            if post.collectible_tag_code:
                notify_post_collectible_tag_owners(post)

        # Refresh linked posts
        if data["refresh_linked"]:
            LinkedPost.create_links_from_text(post, post.text)
            post_comments = Comment.visible_objects().filter(post=post, is_deleted=False)
            for comment in post_comments:
                LinkedPost.create_links_from_text(comment.post, comment.text)

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Настройки поста «{post.title}» сохранены",
            "message": f"Ура 🎉",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": post,
            "form": form,
        })

