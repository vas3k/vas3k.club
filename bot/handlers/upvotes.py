import logging

import telegram
from django.conf import settings
from django.urls import reverse
from telegram import Update
from telegram.ext import CallbackContext

from bot.handlers.common import get_club_user, COMMENT_EMOJI_RE, POST_EMOJI_RE, get_club_comment, get_club_post
from bot.decorators import is_club_member
from comments.models import CommentVote, Comment
from notifications.telegram.common import Chat, send_telegram_message
from posts.models.post import Post
from posts.models.votes import PostVote

log = logging.getLogger(__name__)


@is_club_member
def upvote(update: Update, context: CallbackContext) -> None:
    if not update.message \
            or not update.message.reply_to_message \
            or not update.message.reply_to_message.text:
        return None

    user = get_club_user(update)
    if not user:
        return None

    reply_text_start = update.message.reply_to_message.text[:10]

    if COMMENT_EMOJI_RE.match(reply_text_start):
        comment = get_club_comment(update)
        if comment:
            _, is_created = CommentVote.upvote(
                user=user,
                comment=comment,
            )
            update.callback_query.answer(
                text=f"➜ Заплюсовано 👍" if is_created else "➜ Ты уже плюсовал, поц",
            )

    if POST_EMOJI_RE.match(reply_text_start):
        post = get_club_post(update)
        if post:
            _, is_created = PostVote.upvote(
                user=user,
                post=post,
            )
            update.callback_query.answer(
                text=f"➜ Заплюсовано 👍" if is_created else "➜ Ты уже плюсовал, поц",
            )

    return None


def upvote_comment(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user:
        return None

    _, comment_id = update.callback_query.data.split(":", 1)
    comment = Comment.objects.filter(id=comment_id).select_related("post").first()
    if not comment:
        return None

    _, is_created = CommentVote.upvote(
        user=user,
        comment=comment,
    )

    if is_created and user.telegram_id:
        comment_url = settings.APP_HOST + reverse("show_comment", kwargs={
            "post_slug": comment.post.slug,
            "comment_id": comment.id
        })
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"➜ Заплюсован <a href=\"{comment_url}\">комментарий</a> от {comment.author.full_name} 👍",
            parse_mode=telegram.ParseMode.HTML,
        )

    return None


def upvote_post(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user:
        return None

    _, post_id = update.callback_query.data.split(":", 1)
    post = Post.objects.filter(id=post_id).first()
    if not post:
        return None

    _, is_created = PostVote.upvote(
        user=user,
        post=post,
    )

    if is_created and user.telegram_id:
        update.callback_query.answer(
            text=f"➜ Заплюсован пост «{post.title}» 👍",
        )

    return None
