from django import forms
from django.shortcuts import render
from django_q.tasks import async_task

from notifications.telegram.posts import notify_post_rejected
from posts.moderation import REJECT_POST_REASONS
from posts.models.post import Post
from search.models import SearchIndex

CUSTOM_REASON = "custom"


class PostModerateForm(forms.Form):
    reason = forms.ChoiceField(
        label="Причина",
        choices=[],
    )

    custom_reason = forms.CharField(
        label="Кастомная причина",
        widget=forms.Textarea,
        required=False,
    )

    def __init__(self, *args, post, **kwargs):
        super().__init__(*args, **kwargs)
        reasons = REJECT_POST_REASONS.get(post.type) or []
        self.fields["reason"].choices = [
            (CUSTOM_REASON, "🚫 Кастомная причина"),
            *[(code, title) for code, title in reasons],
        ]
        self.fields["reason"].initial = CUSTOM_REASON

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("reason") == CUSTOM_REASON and not (cleaned_data.get("custom_reason") or "").strip():
            self.add_error("custom_reason", "Напишите кастомную причину")

        return cleaned_data


def get_moderate_action(request, post: Post, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": post,
        "form": PostModerateForm(post=post),
    })


def post_moderate_action(request, post: Post, **context):
    form = PostModerateForm(request.POST, post=post)
    if form.is_valid():
        data = form.cleaned_data
        moderator = request.me

        if data["reason"] == CUSTOM_REASON:
            reason_value = CUSTOM_REASON
            template = "notifications/post_rejected/custom.html"
            custom_reason = data["custom_reason"].strip()
        else:
            reason_value = data["reason"]
            template = f"notifications/post_rejected/{reason_value}.html"
            custom_reason = None

        post.moderation_status = Post.MODERATION_REJECTED
        post.moderation_data = {
            "reason": reason_value,
            "template": template,
            "user": {
                "slug": moderator.slug,
                "avatar": moderator.get_avatar(),
                "full_name": moderator.full_name,
            },
        }

        if custom_reason:
            post.moderation_data["custom_reason"] = custom_reason

        post.unpublish()

        SearchIndex.update_post_index(post)

        async_task(notify_post_rejected, post)

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Пост «{post.title}» перенесен в черновики",
            "message": f"Причина: {custom_reason or reason_value}",
        })

    return render(request, "godmode/action.html", {
        **context,
        "item": post,
        "form": form,
    })
