import logging

from django.urls import reverse
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from bot.handlers.common import get_club_user, COMMENT_REPLY_RE, POST_COMMENT_RE, get_club_comment, get_club_post
from bot.decorators import is_club_member
from club import settings
from comments.models import Comment
from posts.models.post import Post
from posts.models.linked import LinkedPost

log = logging.getLogger(__name__)

MIN_COMMENT_LEN = 140


def comment(update: Update, context: CallbackContext) -> None:
    if not update.message \
            or not update.message.reply_to_message \
            or not update.message.reply_to_message.text:
        return None

    reply_text_start = update.message.reply_to_message.text[:10]

    if COMMENT_REPLY_RE.match(reply_text_start):
        return reply_to_comment(update, context)

    if POST_COMMENT_RE.match(reply_text_start):
        return comment_to_post(update, context)

    # skip normal replies
    return None


@is_club_member
def reply_to_comment(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user:
        return None

    comment = get_club_comment(update)
    if not comment:
        return None

    is_ok = Comment.check_rate_limits(user)
    if not is_ok:
        update.message.reply_text(
            f"🙅‍♂️ Извините, вы комментировали слишком часто и достигли дневного лимита"
        )
        return None

    text = update.message.text or update.message.caption
    if not text:
        update.message.reply_text(
            f"😣 Сорян, я пока умею только в текстовые реплаи"
        )
        return None

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

    update.message.reply_text(
        f"➜ <a href=\"{new_comment_url}\">Отвечено</a> 👍",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


@is_club_member
def comment_to_post(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user:
        return None

    post = get_club_post(update)
    if not post or post.type in [Post.TYPE_BATTLE, Post.TYPE_WEEKLY_DIGEST]:
        return None

    is_ok = Comment.check_rate_limits(user)
    if not is_ok:
        update.message.reply_text(
            f"🙅‍♂️ Извините, вы комментировали слишком часто и достигли дневного лимита"
        )
        return None

    text = update.message.text or update.message.caption
    if not text:
        update.message.reply_text(
            f"😣 Сорян, я пока умею только в текстовые реплаи"
        )
        return None

    if len(text) < MIN_COMMENT_LEN:
        update.message.reply_text(
            f"😋 Твой коммент слишком короткий. Не буду постить его в Клуб, пускай остается в чате"
        )
        return None

    reply = Comment.objects.create(
        author=user,
        post=post,
        text=text,
        useragent="TelegramBot (like TwitterBot)",
        metadata={
            "telegram": update.to_dict()
        }
    )
    LinkedPost.create_links_from_text(post, text)

    new_comment_url = settings.APP_HOST + reverse("show_comment", kwargs={
        "post_slug": reply.post.slug,
        "comment_id": reply.id
    })

    update.message.reply_text(
        f"➜ <a href=\"{new_comment_url}\">Отвечено</a> 👍",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
