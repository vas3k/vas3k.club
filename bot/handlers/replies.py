import logging
import re

from django.conf import settings
from django.urls import reverse
from telegram import Update

from bot.common import send_telegram_message, Chat
from bot.handlers.common import get_bot_user
from comments.models import Comment, CommentVote

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

    reply_to_id = COMMENT_URL_RE.match(comment_url_entity[0]).group(1)
    reply = Comment.objects.filter(id=reply_to_id).first()
    if not reply:
        log.info(f"Reply not found: {reply_to_id}")
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

    if text in ["+", "+1", "++", "👍", "up"]:
        is_vote_created = CommentVote.upvote(
            user=user,
            comment=reply,
            useragent="TelegramBot (like TwitterBot)",
            request=None
        )
        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text=f"➜ Отплюсовано 👍" if is_vote_created else f"🙅‍♂️ Уже отплюсовано!"
        )
        return

    comment = Comment.objects.create(
        author=user,
        post=reply.post,
        reply_to=Comment.find_top_comment(reply),
        text=f"@{reply.author.slug}, {text}",
        useragent="TelegramBot (like TwitterBot)",
        metadata={
            "telegram": update.to_dict()
        }
    )
    new_comment_url = settings.APP_HOST + reverse("show_comment", kwargs={
        "post_slug": comment.post.slug,
        "comment_id": comment.id
    })
    send_telegram_message(
        chat=Chat(id=update.effective_chat.id),
        text=f"➜ <a href=\"{new_comment_url}\">Отвечено</a> 👍"
    )
