import logging
import re
from datetime import datetime
from urllib.parse import quote, urlsplit

from bs4 import BeautifulSoup, Comment, Doctype

from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.shortcuts import redirect, render
from django.urls import reverse
from django_q.tasks import async_task
from telegram.error import TelegramError

from common.markdown.markdown import markdown_text
from common.markdown.telegram_renderer import TelegramRenderer
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


class ModerationTelegramRenderer(TelegramRenderer):
    def list(self, text, ordered, **attrs):
        return text + "\n"


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
    text = forms.CharField(
        label="Причина",
        widget=forms.Textarea(attrs={"rows": 12, "placeholder": "Расскажите, как сделать пост лучше…"}),
        help_text="Markdown: **жирный**, *курсив*, [ссылка](https://…) и блоки кода в тройных обратных кавычках.",
        max_length=3500,
        required=False,
    )

    def __init__(self, *args, post, **kwargs):
        super().__init__(*args, **kwargs)
        self.post = post
        reasons = REJECT_POST_REASONS.get(post.type) or []
        self.fields["reason"].choices = [
            *reasons,
            (CUSTOM_REASON, "✍️ Кастомная причина"),
        ]
        data = post.moderation_data or {}
        self.rejection_texts = {
            code: render_to_string(f"notifications/post_rejected/{code}.html", {"post": post, "settings": settings})
            for code, label in reasons
        }

        self.rejection_texts["saved"] = data.get("text") or ""

        for code, rendered in self.rejection_texts.items():
            content = BeautifulSoup(
                f"<div>{rendered}</div>", "html.parser", preserve_whitespace_tags={"div", "pre"},
            ).div

            for node in content.find_all(string=True):
                if not node.find_parent("pre"):
                    node.replace_with(re.sub(r"([\\`*_\[\]<>#~])", r"\\\1", str(node)))

            for tag in reversed(content.find_all(True)):
                value = tag.get_text()

                if tag.name in {"b", "strong"} and value:
                    tag.replace_with(f"**{value}**")
                elif tag.name in {"i", "em"} and value:
                    tag.replace_with(f"*{value}*")
                elif tag.name == "a" and tag.get("href"):
                    url = quote(tag["href"], safe="/:?#[]@!$&'()*+,;=%")
                    tag.replace_with(f"[{value}](<{url}>)")
                elif tag.name == "pre":
                    fence = "`" * max(3, max((len(run) + 1 for run in re.findall(r"`+", value)), default=3))
                    tag.replace_with(f"\n\n{fence}\n{value}\n{fence}\n\n")
                else:
                    tag.unwrap()

            self.rejection_texts[code] = content.get_text().strip()

        saved_text = self.rejection_texts.pop("saved")

        if post.moderation_status in dict(self.fields["decision"].choices):
            self.initial["decision"] = post.moderation_status
            reason = data.get("reason")
            self.initial["reason"] = reason if reason in dict(self.fields["reason"].choices) else CUSTOM_REASON
            self.initial["text"] = saved_text

        if self.is_bound and self.data.get("decision") != Post.MODERATION_REJECTED:
            self.data = self.data.copy()
            self.data["reason"] = ""
            self.data["text"] = ""

    def clean_text(self):
        rendered = markdown_text(self.cleaned_data["text"], renderer=ModerationTelegramRenderer)
        content = BeautifulSoup(
            f"<div>{rendered}</div>", "html.parser", preserve_whitespace_tags={"div", "pre"},
        ).div
        allowed_tags = {"b", "i", "pre", "a"}

        for comment in content.find_all(string=lambda node: isinstance(node, (Comment, Doctype))):
            comment.extract()

        for tag in content.find_all(True):
            if tag.name == "p":
                tag.unwrap()
                continue

            if tag.name == "strong":
                tag.name = "b"
            elif tag.name == "em":
                tag.name = "i"
            elif tag.name == "code":
                if tag.parent.name == "pre":
                    code = tag.get_text().removesuffix("\n")
                    tag.replace_with(code)
                    continue

                tag.name = "pre"

            if tag.name not in allowed_tags:
                tag.replace_with(str(tag))
                continue

            if tag.name == "a":
                url = tag.get("href", "")

                try:
                    scheme = urlsplit(url).scheme.lower()
                except ValueError:
                    scheme = ""

                if scheme not in {"http", "https", "tg"} or any(ord(char) <= 32 for char in url):
                    tag.unwrap()
                    continue

                tag.attrs = {"href": url}
            else:
                tag.attrs = {}

        if not content.get_text().strip():
            return ""

        text = content.decode_contents().strip()

        notification = render_to_string("posts/widgets/moderation_text.html", {
            "post": self.post,
            "text": text,
            "settings": settings,
        }).strip()

        if len(notification) > 4096:
            raise forms.ValidationError("Сообщение слишком длинное для Telegram, сократите его")

        return text

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get("decision") == Post.MODERATION_REJECTED:
            reason = cleaned_data.get("reason")

            if not reason and "reason" not in self.errors:
                self.add_error("reason", "Выберите причину")

            moderation_text = cleaned_data.get("text")

            if not moderation_text and "text" not in self.errors:
                self.add_error("text", "Напишите сообщение автору")

        return cleaned_data


def get_moderate_action(request, post: Post, **context):
    form = PostModerateForm(post=post)
    decision = request.GET.get("decision")

    if decision in dict(form.fields["decision"].choices):
        form.initial["decision"] = decision

    return render(request, "godmode/actions/post_moderate.html", {
        **context,
        "item": post,
        "form": form,
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
    status_changed = post.moderation_status != data["decision"]
    post.moderation_status = data["decision"]

    if post.moderation_status == Post.MODERATION_REJECTED:
        reason = data["reason"]
        post.record_moderator_decision(moderator, reason=reason, text=data["text"])

        if status_changed:
            post.unpublish()
            async_task(notify_post_rejected, post)
        else:
            post.save()

        reason_label = dict(form.fields["reason"].choices)[reason]
        message = f"👎 Пост «{post.title}» перенесен в черновики. Причина: {reason_label}"
    else:
        if status_changed:
            post.visibility = Post.VISIBILITY_EVERYWHERE
            post.last_activity_at = datetime.utcnow()
            post.published_at = datetime.utcnow()

            if post.moderation_status == Post.MODERATION_FORGIVEN:
                post.collectible_tag_code = None

        post.record_moderator_decision(moderator)
        post.save()
        post_url = settings.APP_HOST + reverse("show_post", kwargs={
            "post_type": post.type,
            "post_slug": post.slug,
        })

        if post.moderation_status == Post.MODERATION_APPROVED:
            if status_changed:
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
