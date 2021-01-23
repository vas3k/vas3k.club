import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.handlers.common import get_club_user, COMMENT_REPLY_RE, POST_COMMENT_RE, get_club_comment, get_club_post
from bot.decorators import is_club_member
from comments.models import CommentVote
from posts.models.votes import PostVote

log = logging.getLogger(__name__)


def upvote(update: Update, context: CallbackContext) -> None:
    if not update.message \
            or not update.message.reply_to_message \
            or not update.message.reply_to_message.text:
        return None

    reply_text_start = update.message.reply_to_message.text[:10]

    if COMMENT_REPLY_RE.match(reply_text_start):
        return upvote_comment(update, context)

    if POST_COMMENT_RE.match(reply_text_start):
        return upvote_post(update, context)

    return None


@is_club_member
def upvote_comment(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user:
        return None

    comment = get_club_comment(update)
    if not comment:
        return None

    _, is_created = CommentVote.upvote(
        user=user,
        comment=comment,
    )

    if is_created:
        update.message.reply_text(f"Заплюсовано 👍")
    else:
        update.message.reply_text(f"Ты уже плюсовал, поц")


@is_club_member
def upvote_post(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user:
        return None

    post = get_club_post(update)
    if not post:
        return None

    _, is_created = PostVote.upvote(
        user=user,
        post=post,
    )

    if is_created:
        update.message.reply_text(f"Заплюсовано 👍")
    else:
        update.message.reply_text(f"Ты уже плюсовал, поц")
