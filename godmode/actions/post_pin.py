from datetime import datetime, timedelta

from django import forms
from django.shortcuts import render

from posts.models.post import Post


class PostPinForm(forms.Form):
    add_pin = forms.BooleanField(
        label="Запинить пост",
        initial=True,
        required=False
    )

    pin_days = forms.IntegerField(
        label="На сколько дней пин?",
        initial=1,
        required=False
    )

    remove_pin = forms.BooleanField(
        label="Отпинить обратно",
        required=False
    )



def get_pin_action(request, post: Post, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": post,
        "form": PostPinForm(),
    })


def post_pin_action(request, post: Post, **context):
    form = PostPinForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Pins
        if data["add_pin"]:
            post.is_pinned_until = datetime.utcnow() + timedelta(days=data["pin_days"])
            post.save()

        if data["remove_pin"]:
            post.is_pinned_until = None
            post.save()

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Пост «{post.title}» запинен",
            "message": f"Он будет висеть наверху главной {data['pin_days']} дней",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": post,
            "form": form,
        })

