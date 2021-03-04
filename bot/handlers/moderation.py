import logging
from datetime import datetime

from django.conf import settings
from django.urls import reverse
from telegram import Update
from telegram.ext import CallbackContext

from bot.handlers.common import RejectReason
from bot.decorators import is_moderator
from notifications.email.users import send_welcome_drink, send_rejected_email
from notifications.telegram.posts import notify_post_author_approved, announce_in_club_chats, \
    notify_post_author_rejected
from notifications.telegram.users import notify_user_profile_approved, notify_user_profile_rejected
from posts.models.post import Post
from search.models import SearchIndex
from users.models.user import User

log = logging.getLogger(__name__)


@is_moderator
def approve_post(update: Update, context: CallbackContext) -> None:
    _, post_id = update.callback_query.data.split(":", 1)

    post = Post.objects.get(id=post_id)
    if post.is_approved_by_moderator:
        update.effective_chat.send_message(f"Пост «{post.title}» уже одобрен")
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        return

    post.is_approved_by_moderator = True
    post.last_activity_at = datetime.utcnow()
    if not post.published_at:
        post.published_at = datetime.utcnow()
    post.save()

    notify_post_author_approved(post)
    announce_in_club_chats(post)

    post_url = settings.APP_HOST + reverse("show_post", kwargs={
        "post_type": post.type,
        "post_slug": post.slug,
    })

    update.effective_chat.send_message(
        f"👍 Пост «{post.title}» одобрен ({update.effective_user.full_name}): {post_url}",
        disable_web_page_preview=True
    )

    # hide buttons
    update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None


@is_moderator
def forgive_post(update: Update, context: CallbackContext) -> None:
    _, post_id = update.callback_query.data.split(":", 1)

    post = Post.objects.get(id=post_id)
    post.is_approved_by_moderator = False
    if not post.published_at:
        post.published_at = datetime.utcnow()
    post.save()

    post_url = settings.APP_HOST + reverse("show_post", kwargs={
        "post_type": post.type,
        "post_slug": post.slug,
    })

    update.effective_chat.send_message(
        f"😕 Пост «{post.title}» не одобрен, но оставлен на сайте ({update.effective_user.full_name}): {post_url}",
        disable_web_page_preview=True
    )

    # hide buttons
    update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None


@is_moderator
def unpublish_post(update: Update, context: CallbackContext) -> None:
    _, post_id = update.callback_query.data.split(":", 1)

    post = Post.objects.get(id=post_id)
    if not post.is_visible:
        update.effective_chat.send_message(f"Пост «{post.title}» уже перенесен в черновики")
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    post.unpublish()

    SearchIndex.update_post_index(post)

    notify_post_author_rejected(post)

    update.effective_chat.send_message(
        f"👎 Пост «{post.title}» перенесен в черновики ({update.effective_user.full_name})"
    )

    # hide buttons
    update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None


@is_moderator
def approve_user_profile(update: Update, context: CallbackContext) -> None:
    _, user_id = update.callback_query.data.split(":", 1)

    user = User.objects.get(id=user_id)
    if user.moderation_status == User.MODERATION_STATUS_APPROVED:
        update.effective_chat.send_message(f"Пользователь «{user.full_name}» уже одобрен")
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    if user.moderation_status == User.MODERATION_STATUS_REJECTED:
        update.effective_chat.send_message(f"Пользователь «{user.full_name}» уже был отклонен")
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    user.moderation_status = User.MODERATION_STATUS_APPROVED
    user.created_at = datetime.utcnow()
    user.save()

    # make intro visible
    intro = Post.objects.filter(author=user, type=Post.TYPE_INTRO).first()
    intro.is_approved_by_moderator = True
    intro.is_visible = True
    if not intro.published_at:
        intro.published_at = datetime.utcnow()
    intro.save()

    SearchIndex.update_user_index(user)

    notify_user_profile_approved(user)
    send_welcome_drink(user)
    announce_in_club_chats(intro)

    update.effective_chat.send_message(
        f"✅ Пользователь «{user.full_name}» одобрен ({update.effective_user.full_name})"
    )

    # hide buttons
    update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None


@is_moderator
def reject_user_profile(update: Update, context: CallbackContext):
    code, user_id = update.callback_query.data.split(":", 1)
    reason = {
        "reject_user": RejectReason.intro,
        "reject_user_intro": RejectReason.intro,
        "reject_user_data": RejectReason.data,
        "reject_user_aggression": RejectReason.aggression,
        "reject_user_general": RejectReason.general,
    }.get(code) or RejectReason.intro

    user = User.objects.get(id=user_id)
    if user.moderation_status == User.MODERATION_STATUS_REJECTED:
        update.effective_chat.send_message(
            f"Пользователь «{user.full_name}» уже был отклонен и пошел все переделывать"
        )
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    if user.moderation_status == User.MODERATION_STATUS_APPROVED:
        update.effective_chat.send_message(
            f"Пользователь «{user.full_name}» уже был принят, его нельзя реджектить"
        )
        update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    user.moderation_status = User.MODERATION_STATUS_REJECTED
    user.save()

    notify_user_profile_rejected(user, reason)
    send_rejected_email(user, reason)

    update.effective_chat.send_message(
        f"❌ Пользователь «{user.full_name}» отклонен по причине «{reason.value}» ({update.effective_user.full_name})"
    )

    # hide buttons
    update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None
