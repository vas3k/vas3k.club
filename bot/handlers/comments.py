import logging

from django.urls import reverse
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from bot.handlers.common import get_club_user, COMMENT_EMOJI_RE, POST_EMOJI_RE, get_club_comment, get_club_post
from bot.decorators import is_club_member
from club import settings
from comments.models import Comment
from posts.models.post import Post
from posts.models.linked import LinkedPost
from posts.models.views import PostView
from search.models import SearchIndex

log = logging.getLogger(__name__)

MIN_COMMENT_LEN = 40
SKIP_COMMANDS = ("/skip", "#skip", "#ignore")


def comment(update: Update, context: CallbackContext) -> None:
    log.info("Comment handler triggered")

    if not update.message or not update.message.reply_to_message:
        log.info("No message or reply_to_message in update. Skipping.")
        return None

    reply_text_start = (
        update.message.reply_to_message.text or
        update.message.reply_to_message.caption or
        ""
    )[:10]

    log.info("Original message start: %s", reply_text_start)

    if COMMENT_EMOJI_RE.match(reply_text_start):
        return reply_to_comment(update, context)

    if POST_EMOJI_RE.match(reply_text_start):
        return comment_to_post(update, context)

    # skip normal replies
    log.info("Skipping...")
    return None


@is_club_member
def reply_to_comment(update: Update, context: CallbackContext) -> None:
    log.info("Reply_to_comment handler triggered")

    user = get_club_user(update)
    if not user:
        log.info("User not found")
        return None

    comment = get_club_comment(update)
    if not comment:
        log.info("Original comment not found. Skipping.")
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

    for skip_word in SKIP_COMMANDS:
        if skip_word in text:
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
    Comment.update_post_counters(reply.post)
    PostView.increment_unread_comments(reply)
    PostView.register_view(
        request=None,
        user=user,
        post=reply.post,
    )
    SearchIndex.update_comment_index(reply)
    LinkedPost.create_links_from_text(reply.post, text)

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
    log.info("Reply_to_post handler triggered")

    user = get_club_user(update)
    if not user:
        log.info("User not found")
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

    for skip_word in SKIP_COMMANDS:
        if skip_word in text:
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
    Comment.update_post_counters(post)
    PostView.increment_unread_comments(reply)
    PostView.register_view(
        request=None,
        user=user,
        post=post,
    )
    SearchIndex.update_comment_index(reply)
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
