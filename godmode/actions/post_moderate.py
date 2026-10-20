import logging

from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django_q.tasks import async_task
from telegram.error import TelegramError

from common.markdown.markdown import markdown_tg
from notifications.telegram.bot import bot
from notifications.telegram.common import ADMIN_CHAT, send_telegram_message
from notifications.telegram.posts import notify_post_rejected
from posts.moderation import REJECT_POST_REASONS
from posts.models.post import Post
from search.models import SearchIndex

log = logging.getLogger(__name__)

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
            *[(code, f'❌ {title}') for code, title in reasons],
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
        message_id = (post.moderation_data or {}).get("message_id")

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
            "text": render_to_string(template, {
                "post": post,
                "settings": settings,
                "custom_reason": mark_safe(markdown_tg(custom_reason)) if custom_reason else None,
            }),
            "user": {
                "slug": moderator.slug,
                "avatar": moderator.get_avatar(),
                "full_name": moderator.full_name,
            },
        }

        if message_id:
            post.moderation_data["message_id"] = message_id

        post.unpublish()

        SearchIndex.update_post_index(post)

        async_task(notify_post_rejected, post)

        if bot and ADMIN_CHAT and message_id:
            try:
                bot.edit_message_reply_markup(
                    chat_id=ADMIN_CHAT.id,
                    message_id=message_id,
                    reply_markup=None,
                )
            except TelegramError as ex:
                log.warning(f"Telegram error: {ex}")

        if custom_reason:
            send_telegram_message(
                chat=ADMIN_CHAT,
                text=(
                    f"👎 Пост «{post.title}» перенесен в черновики "
                    f"({moderator.full_name})\n\nКастомная причина: {custom_reason}"
                ),
                parse_mode=None,
            )

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
