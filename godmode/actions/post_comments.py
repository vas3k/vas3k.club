from datetime import datetime, timedelta

from django import forms
from django.shortcuts import render

from notifications.telegram.posts import notify_post_collectible_tag_owners
from posts.models.post import Post


class PostCommentsForm(forms.Form):
    toggle_is_commentable = forms.BooleanField(
        label="Закрыть комменты (повторный клик переоткроет заново)",
        required=True,
    )



def get_comments_action(request, post: Post, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": post,
        "form": PostCommentsForm(),
    })


def post_comments_action(request, post: Post, **context):
    form = PostCommentsForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Close comments
        if data["toggle_is_commentable"]:
            post.is_commentable = not post.is_commentable
            post.save()

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

