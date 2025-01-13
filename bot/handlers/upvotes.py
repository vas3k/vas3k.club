import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.handlers.common import get_club_user, COMMENT_EMOJI_RE, POST_EMOJI_RE, get_club_comment, get_club_post
from bot.decorators import is_club_member
from comments.models import CommentVote, Comment
from posts.models.post import Post
from posts.models.votes import PostVote

log = logging.getLogger(__name__)


@is_club_member
def upvote(update: Update, context: CallbackContext) -> None:
    log.info("Upvote handler triggered")

    if not update.message or not update.message.reply_to_message:
        return None

    user = get_club_user(update)
    if not user:
        return None

    reply_text_start = (
        update.message.reply_to_message.text or
        update.message.reply_to_message.caption or
        ""
    )[:10]

    if COMMENT_EMOJI_RE.match(reply_text_start):
        comment = get_club_comment(update)
        if comment:
            _, is_created = CommentVote.upvote(
                user=user,
                comment=comment,
            )
            update.message.reply_text(f"➜ Заплюсовано 👍" if is_created else "➜ Ты уже плюсовал, поц")

    if POST_EMOJI_RE.match(reply_text_start):
        post = get_club_post(update)
        if post:
            _, is_created = PostVote.upvote(
                user=user,
                post=post,
            )
            update.message.reply_text("➜ Заплюсовано 👍" if is_created else "➜ Ты уже плюсовал, поц")

    return None


def upvote_comment(update: Update, context: CallbackContext) -> None:
    log.info("Upvote_comment handler triggered")

    user = get_club_user(update)
    if not user:
        return None

    _, comment_id = update.callback_query.data.split(":", 1)
    comment = Comment.objects.filter(id=comment_id).select_related("post").first()
    if not comment:
        log.info("Original comment not found. Skipping.")
        return None

    _, is_created = CommentVote.upvote(
        user=user,
        comment=comment,
    )

    if is_created:
        update.callback_query.answer(text="Комментарий заплюсован 👍")
    else:
        update.callback_query.answer(text="Вы уже плюсовали этот комментарий")

    return None


def upvote_post(update: Update, context: CallbackContext) -> None:
    log.info("Upvote_post handler triggered")

    user = get_club_user(update)
    if not user:
        return None

    _, post_id = update.callback_query.data.split(":", 1)
    post = Post.objects.filter(id=post_id).first()
    if not post:
        log.info("Original post not found. Skipping.")
        return None

    _, is_created = PostVote.upvote(
        user=user,
        post=post,
    )

    if is_created:
        update.callback_query.answer(text="Пост заплюсован 👍")
    else:
        update.callback_query.answer(text="Вы уже плюсовали этот пост")

    return None
