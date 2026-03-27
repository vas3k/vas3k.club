from django import forms
from django.shortcuts import render

from common.data.labels import LABELS
from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from notifications.telegram.posts import notify_admins_on_post_label_changed
from posts.models.post import Post
from users.models.achievements import UserAchievement, Achievement


class PostLabelForm(forms.Form):
    new_label = forms.ChoiceField(
        label="Выдать лейбл",
        choices=[(None, "---")] + [(key, value.get("title")) for key, value in LABELS.items()],
        required=False,
    )

    remove_label = forms.BooleanField(
        label="Удалить текуший лейбл",
        required=False
    )


def get_label_action(request, post: Post, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": post,
        "form": PostLabelForm(),
    })


def post_label_action(request, post: Post, **context):
    form = PostLabelForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Labels
        if data["new_label"]:
            label = LABELS.get(data["new_label"])
            if label:
                post.label_code = data["new_label"]
                post.save()

                if label.get("related_achievement"):
                    achievement = Achievement.objects.filter(code=label["related_achievement"]).first()
                    if achievement:
                        UserAchievement.objects.get_or_create(
                            user=post.author,
                            achievement=achievement,
                        )

                notify_admins_on_post_label_changed(post)

        if data["remove_label"]:
            post.label_code = None
            post.save()

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Посту «{post.title}» выдан лейбл «{data['new_label']}»",
            "message": f"Ура 🎉",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": post,
            "form": form,
        })

