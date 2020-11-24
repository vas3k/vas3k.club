import logging
import re

from django.conf import settings
from django.urls import reverse
from telegram import Update

from bot.common import send_telegram_message, Chat
from bot.handlers.common import get_bot_user
from comments.models import Comment

COMMENT_URL_RE = re.compile(r"https?:[/|.|\w|\s|-]*/post/.+?/comment/([a-fA-F0-9\-]+)/")

log = logging.getLogger(__name__)


def process_comment_reply(update: Update):
    if not update.message.reply_to_message:
        return

    user = get_bot_user(update)
    if not user:
        return

    comment_url_entity = [
        entity["url"] for entity in update.message.reply_to_message.entities
        if entity["type"] == "text_link" and COMMENT_URL_RE.match(entity["url"])
    ]
    if not comment_url_entity:
        log.info(f"Comment url not found in: {update.message.reply_to_message.entities}")
        return

    comment_id = COMMENT_URL_RE.match(comment_url_entity[0]).group(1)
    comment = Comment.objects.filter(id=comment_id).first()
    if not comment:
        log.info(f"Comment not found: {comment_id}")
        return

    is_ok = Comment.check_rate_limits(user)
    if not is_ok:
        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text=f"🙅‍♂️ Извините, вы комментировали слишком часто и достигли дневного лимита"
        )
        return

    text = update.message.text or update.message.caption
    if not text:
        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text=f"😣 Сорян, я пока умею только в текстовые ответы"
        )
        return

    # max 3 levels of comments are allowed
    reply_to_id = comment.id
    if comment.reply_to_id and comment.reply_to.reply_to_id:
        reply_to_id = comment.reply_to_id

    reply = Comment.objects.create(
        author=user,
        post=comment.post,
        reply_to_id=reply_to_id,
        text=f"@{comment.author.slug}, {text}",
        useragent="TelegramBot (like TwitterBot)",
        metadata={
            "telegram": update.to_dict()
        }
    )
    new_comment_url = settings.APP_HOST + reverse("show_comment", kwargs={
        "post_slug": reply.post.slug,
        "comment_id": reply.id
    })
    send_telegram_message(
        chat=Chat(id=update.effective_chat.id),
        text=f"➜ <a href=\"{new_comment_url}\">Отвечено</a> 👍"
    )
