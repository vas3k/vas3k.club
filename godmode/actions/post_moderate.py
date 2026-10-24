import logging
from datetime import datetime

from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_q.tasks import async_task
from telegram.error import TelegramError

from common.markdown.markdown import markdown_tg
from notifications.telegram.bot import bot
from notifications.telegram.common import ADMIN_CHAT, send_telegram_message
from notifications.telegram.posts import (
    announce_in_club_chats, notify_post_approved, notify_post_collectible_tag_owners,
    notify_post_rejected, notify_post_room_subscribers,
)
from posts.moderation import REJECT_POST_REASONS
from posts.models.post import Post
from search.models import SearchIndex

log = logging.getLogger(__name__)

CUSTOM_REASON = "custom"


class PostModerateForm(forms.Form):
    decision = forms.ChoiceField(
        label="Решение",
        widget=forms.RadioSelect,
        choices=[
            (Post.MODERATION_REJECTED, "❌ Отклонить"),
            (Post.MODERATION_FORGIVEN, "😕 Оставить"),
            (Post.MODERATION_APPROVED, "👍 Одобрить"),
        ],
    )
    reason = forms.ChoiceField(
        label="Что нужно доработать?",
        widget=forms.RadioSelect,
        choices=[],
        required=False,
    )
    custom_reason = forms.CharField(
        label="Что нужно поправить автору?",
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "Расскажите, как сделать пост лучше…"}),
        required=False,
    )

    def __init__(self, *args, post, **kwargs):
        super().__init__(*args, **kwargs)
        reasons = REJECT_POST_REASONS.get(post.type) or []
        self.fields["reason"].choices = [
            *reasons,
            (CUSTOM_REASON, "✍️ Кастомная причина"),
        ]
        data = post.moderation_data or {}

        if post.moderation_status in dict(self.fields["decision"].choices):
            self.initial["decision"] = post.moderation_status
            self.initial["reason"] = data.get("reason")
            self.initial["custom_reason"] = data.get("custom_reason")

        if self.is_bound and self.data.get("decision") != Post.MODERATION_REJECTED:
            self.data = self.data.copy()
            self.data["reason"] = ""
            self.data["custom_reason"] = ""

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("decision") == Post.MODERATION_REJECTED:
            reason = cleaned_data.get("reason")

            if not reason and "reason" not in self.errors:
                self.add_error("reason", "Выберите причину")

            if reason == CUSTOM_REASON and not cleaned_data.get("custom_reason"):
                self.add_error("custom_reason", "Напишите кастомную причину")

        return cleaned_data


def get_moderate_action(request, post: Post, **context):
    return render(request, "godmode/actions/post_moderate.html", {
        **context,
        "item": post,
        "form": PostModerateForm(post=post),
    })


def post_moderate_action(request, post: Post, **context):
    form = PostModerateForm(request.POST, post=post)

    if not form.is_valid():
        return render(request, "godmode/actions/post_moderate.html", {
            **context,
            "item": post,
            "form": form,
        })

    data = form.cleaned_data
    moderator = request.me
    message_id = (post.moderation_data or {}).get("message_id")
    post.moderation_status = data["decision"]

    if post.moderation_status == Post.MODERATION_REJECTED:
        reason = data["reason"]
        custom_reason = data["custom_reason"] if reason == CUSTOM_REASON else None
        extra = {
            "reason": reason,
            "text": render_to_string(f"notifications/post_rejected/{reason}.html", {
                "post": post,
                "settings": settings,
                "custom_reason": mark_safe(markdown_tg(custom_reason)) if custom_reason else None,
            }),
        }

        if custom_reason:
            extra["custom_reason"] = custom_reason

        post.record_moderator_decision(moderator, extra=extra)
        post.unpublish()
        async_task(notify_post_rejected, post)
        reason_label = dict(form.fields["reason"].choices)[reason]
        message = f"👎 Пост «{post.title}» перенесен в черновики. Причина: {custom_reason or reason_label}"
    else:
        post.visibility = Post.VISIBILITY_EVERYWHERE
        post.last_activity_at = datetime.utcnow()
        post.published_at = datetime.utcnow()

        if post.moderation_status == Post.MODERATION_FORGIVEN:
            post.collectible_tag_code = None

        post.record_moderator_decision(moderator, extra={})
        post.save()
        post_url = settings.APP_HOST + reverse("show_post", kwargs={
            "post_type": post.type,
            "post_slug": post.slug,
        })

        if post.moderation_status == Post.MODERATION_APPROVED:
            async_task(notify_post_approved, post)
            async_task(announce_in_club_chats, post)

            if post.collectible_tag_code:
                async_task(notify_post_collectible_tag_owners, post)

            if post.room_id:
                async_task(notify_post_room_subscribers, post)

            if post.room_id and post.is_room_only:
                message = f"😎 Пост «{post.title}» одобрен для комнаты «{post.room.title}»: {post_url}"
            else:
                message = f"👍 Пост «{post.title}» одобрен: {post_url}"
        else:
            message = f"😕 Пост «{post.title}» не одобрен, но оставлен на сайте: {post_url}"

    SearchIndex.update_post_index(post)

    if bot and ADMIN_CHAT and message_id:
        try:
            bot.edit_message_reply_markup(
                chat_id=ADMIN_CHAT.id,
                message_id=message_id,
                reply_markup=None,
            )
        except TelegramError as ex:
            log.warning(f"Telegram error: {ex}")

    send_telegram_message(chat=ADMIN_CHAT, text=f"{message} ({moderator.full_name})", parse_mode=None)

    return redirect("godmode_action", model_name="posts", item_id=post.id, action_code="moderate")
