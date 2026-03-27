from django import forms
from django.shortcuts import render

from notifications.telegram.common import render_html_message
from notifications.telegram.posts import announce_in_club_channel
from posts.helpers import extract_any_image
from posts.models.post import Post


class PostAnnounceForm(forms.Form):
    text = forms.CharField(
        label="Текст анонса",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
            }
        ),
    )
    image = forms.CharField(
        label="Картинка",
        required=False,
    )
    with_image = forms.BooleanField(
        label="Постим с картинкой?",
        required=False,
        initial=True,
    )




def get_announce_action(request, post: Post, **context):
    initial = {
        "text": render_html_message("channel_post_announce.html", post=post),
        "image": extract_any_image(post),
    }

    return render(request, "godmode/action.html", {
        **context,
        "item": post,
        "form": PostAnnounceForm(initial=initial),
    })


def post_announce_action(request, post: Post, **context):
    form = PostAnnounceForm(request.POST, request.FILES)
    if form.is_valid():
        announce_in_club_channel(
            post=post,
            announce_text=form.cleaned_data["text"],
            image=form.cleaned_data["image"] if form.cleaned_data["with_image"] else None
        )

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Запощено ✅",
            "message": f"Пост «{post.title}» анонсирован на канале",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": post,
            "form": form,
        })

