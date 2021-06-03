import logging
import re
from enum import Enum
from typing import Optional

from telegram import Update, ParseMode

from comments.models import Comment
from posts.models.post import Post
from users.models.user import User

COMMENT_REPLY_RE = re.compile(r"^💬.*")
POST_COMMENT_RE = re.compile(r"^[📝🔗❓💡🏢🤜🤛🔥🙋‍♀️].*")

COMMENT_URL_RE = re.compile(r"https?://vas3k.club/[a-zA-Z]+/.+?/#comment-([a-fA-F0-9\-]+)")
POST_URL_RE = re.compile(r"https?://vas3k.club/[a-zA-Z]+/(.+?)/")

log = logging.getLogger(__name__)


class RejectReason(Enum):
    intro = "intro"
    data = "data"
    aggression = "aggression"
    general = "general"


def get_club_user(update: Update):
    user = User.objects.filter(telegram_id=update.effective_user.id).first()
    if not user:
        update.message.reply_text(
            f"😐 Привяжи <a href=\"https://vas3k.club/user/me/edit/bot/\">бота</a> к профилю, братишка",
            parse_mode=ParseMode.HTML
        )
        return None

    if user.is_banned:
        update.message.reply_text(f"🙈 Ты в бане, мы больше не дружим")
        return None

    if not user.is_club_member:
        update.message.reply_text(f"😣 Твой профиль в Клубе неактивен. Плоти долор!")
        return None

    return user


def get_club_comment(update: Update) -> Optional[Comment]:
    url_entities = [
        entity["url"] for entity in update.message.reply_to_message.entities if entity["type"] == "text_link"
    ]

    for url_entity in url_entities:
        match = COMMENT_URL_RE.match(url_entity)
        if match:
            comment_id = match.group(1)
            if comment_id:
                break
    else:
        log.warning(f"Comment URL not found: {update.message.reply_to_message}")
        return None

    comment = Comment.objects.filter(id=comment_id).first()
    if not comment:
        update.message.reply_text(f"🤨 Коммент '{comment_id}' был удален или куда-то делся")
        return None

    return comment


def get_club_post(update: Update) -> Optional[Post]:
    url_entities = [
        entity["url"] for entity in update.message.reply_to_message.entities if entity["type"] == "text_link"
    ]

    for url_entity in url_entities:
        match = POST_URL_RE.match(url_entity)
        if match:
            post_id = match.group(1)
            if post_id:
                break
    else:
        log.warning(f"Post URL not found: {update.message.reply_to_message}")
        return None

    post = Post.objects.filter(slug=post_id).first()
    if not post or not post.is_commentable:
        update.message.reply_text(f"🤨 Пост был удален, скрыт или украден, сорян")
        return None

    return post
