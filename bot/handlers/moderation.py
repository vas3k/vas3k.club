import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.urls import reverse
from django_q.tasks import async_task
from telegram import LinkPreviewOptions, Update
from telegram.ext import CallbackContext

from bot.handlers.common import UserRejectReason, PostRejectReason
from bot.decorators import is_moderator, ensure_fresh_db_connection
from notifications.email.users import send_welcome_drink, send_user_rejected_email
from notifications.telegram.posts import notify_post_approved, announce_in_club_chats, \
    notify_post_rejected, notify_post_collectible_tag_owners, notify_post_room_subscribers
from notifications.telegram.users import notify_user_profile_approved, notify_user_profile_rejected
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from search.models import SearchIndex
from users.models.user import User

log = logging.getLogger(__name__)


@ensure_fresh_db_connection
@is_moderator
async def approve_post(update: Update, context: CallbackContext) -> None:
    _, post_id = update.callback_query.data.split(":", 1)

    post = Post.objects.get(id=post_id)
    if post.moderation_status in [Post.MODERATION_APPROVED, Post.MODERATION_FORGIVEN, Post.MODERATION_REJECTED]:
        await update.effective_chat.send_message(
            f"Пост «{post.title}» уже был отмодерирован ранее: {post.moderation_status}"
        )
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    post.moderation_status = Post.MODERATION_APPROVED
    post.visibility = Post.VISIBILITY_EVERYWHERE
    post.last_activity_at = datetime.utcnow()
    post.published_at = datetime.utcnow()
    post.save()

    post_url = settings.APP_HOST + reverse("show_post", kwargs={
        "post_type": post.type,
        "post_slug": post.slug,
    })

    if post.room_id and post.is_room_only:
        await update.effective_chat.send_message(
            f"😎 Пост «{post.title}» хорош для комнаты «{post.room.title}», "
            f"но не будет отображаться на главной ({update.effective_user.full_name}): {post_url}",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
    else:
        await update.effective_chat.send_message(
            f"👍 Пост «{post.title}» одобрен ({update.effective_user.full_name}): {post_url}",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

    await update.callback_query.edit_message_reply_markup(reply_markup=None)

    notify_post_approved(post)
    announce_in_club_chats(post)

    if post.collectible_tag_code:
        async_task(notify_post_collectible_tag_owners, post)

    if post.room_id:
        async_task(notify_post_room_subscribers, post)

    SearchIndex.update_post_index(post)

    return None


@ensure_fresh_db_connection
@is_moderator
async def forgive_post(update: Update, context: CallbackContext) -> None:
    _, post_id = update.callback_query.data.split(":", 1)

    post = Post.objects.get(id=post_id)
    if post.moderation_status in [Post.MODERATION_APPROVED, Post.MODERATION_FORGIVEN, Post.MODERATION_REJECTED]:
        await update.effective_chat.send_message(
            f"Пост «{post.title}» уже был отмодерирован ранее: {post.moderation_status}"
        )
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    post.moderation_status = Post.MODERATION_FORGIVEN
    post.visibility = Post.VISIBILITY_EVERYWHERE
    post.last_activity_at = datetime.utcnow()
    post.published_at = datetime.utcnow()
    post.collectible_tag_code = None
    post.save()

    post_url = settings.APP_HOST + reverse("show_post", kwargs={
        "post_type": post.type,
        "post_slug": post.slug,
    })

    await update.effective_chat.send_message(
        f"😕 Пост «{post.title}» не одобрен, но оставлен на сайте ({update.effective_user.full_name}): {post_url}",
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

    await update.callback_query.edit_message_reply_markup(reply_markup=None)

    SearchIndex.update_post_index(post)

    return None


@ensure_fresh_db_connection
@is_moderator
async def reject_post(update: Update, context: CallbackContext) -> None:
    code, post_id = update.callback_query.data.split(":", 1)
    reason = {
        "reject_post": PostRejectReason.draft,
        "reject_post_title": PostRejectReason.title,
        "reject_post_design": PostRejectReason.design,
        "reject_post_dyor": PostRejectReason.dyor,
        "reject_post_duplicate": PostRejectReason.duplicate,
        "reject_post_chat": PostRejectReason.chat,
        "reject_post_tldr": PostRejectReason.tldr,
        "reject_post_github": PostRejectReason.github,
        "reject_post_bias": PostRejectReason.bias,
        "reject_post_hot": PostRejectReason.hot,
        "reject_post_ad": PostRejectReason.ad,
        "reject_post_inside": PostRejectReason.inside,
        "reject_post_value": PostRejectReason.value,
        "reject_post_draft": PostRejectReason.draft,
        "reject_post_false_dilemma": PostRejectReason.false_dilemma,
    }.get(code) or PostRejectReason.draft

    post = Post.objects.get(id=post_id)
    if post.moderation_status in [Post.MODERATION_APPROVED, Post.MODERATION_FORGIVEN, Post.MODERATION_REJECTED]:
        await update.effective_chat.send_message(
            f"Пост «{post.title}» уже был отмодерирован ранее: {post.moderation_status}"
        )
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    post.moderation_status = Post.MODERATION_REJECTED
    post.unpublish()

    SearchIndex.update_post_index(post)

    notify_post_rejected(post, reason)

    await update.effective_chat.send_message(
        f"👎 Пост «{post.title}» перенесен в черновики по причине «{reason.value}» ({update.effective_user.full_name})"
    )

    await update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None


@ensure_fresh_db_connection
@is_moderator
async def approve_user_profile(update: Update, context: CallbackContext) -> None:
    _, user_id = update.callback_query.data.split(":", 1)

    user = User.objects.get(id=user_id)
    if user.moderation_status == User.MODERATION_STATUS_APPROVED:
        await update.effective_chat.send_message(f"Пользователь «{user.full_name}» уже одобрен")
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    if user.moderation_status == User.MODERATION_STATUS_REJECTED:
        await update.effective_chat.send_message(f"Пользователь «{user.full_name}» уже был отклонен")
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    user.moderation_status = User.MODERATION_STATUS_APPROVED
    if user.created_at > datetime.utcnow() - timedelta(days=30):
        # to avoid zeroing out the profiles of the old users
        user.created_at = datetime.utcnow()
    user.save()

    intro = Post.objects.filter(author=user, type=Post.TYPE_INTRO).first()
    intro.moderation_status = Post.MODERATION_APPROVED
    intro.visibility = Post.VISIBILITY_EVERYWHERE
    intro.last_activity_at = datetime.utcnow()
    if not intro.published_at:
        intro.published_at = datetime.utcnow()
    intro.save()

    PostSubscription.subscribe(user, intro, type=PostSubscription.TYPE_ALL_COMMENTS)

    SearchIndex.update_user_index(user)

    notify_user_profile_approved(user)
    send_welcome_drink(user)
    announce_in_club_chats(intro)

    await update.effective_chat.send_message(
        f"✅ Пользователь «{user.full_name}» одобрен ({update.effective_user.full_name})"
    )

    await update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None


@ensure_fresh_db_connection
@is_moderator
async def reject_user_profile(update: Update, context: CallbackContext):
    code, user_id = update.callback_query.data.split(":", 1)
    reason = {
        "reject_user": UserRejectReason.intro,
        "reject_user_intro": UserRejectReason.intro,
        "reject_user_data": UserRejectReason.data,
        "reject_user_ai": UserRejectReason.ai,
        "reject_user_aggression": UserRejectReason.aggression,
        "reject_user_general": UserRejectReason.general,
        "reject_user_name": UserRejectReason.name,
    }.get(code) or UserRejectReason.intro

    user = User.objects.get(id=user_id)
    if user.moderation_status == User.MODERATION_STATUS_REJECTED:
        await update.effective_chat.send_message(
            f"Пользователь «{user.full_name}» уже был отклонен и пошел все переделывать"
        )
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    if user.moderation_status == User.MODERATION_STATUS_APPROVED:
        await update.effective_chat.send_message(
            f"Пользователь «{user.full_name}» уже был принят, его нельзя реджектить"
        )
        await update.callback_query.edit_message_reply_markup(reply_markup=None)
        return None

    user.moderation_status = User.MODERATION_STATUS_REJECTED
    user.save()

    notify_user_profile_rejected(user, reason)
    send_user_rejected_email(user, reason)

    await update.effective_chat.send_message(
        f"❌ Пользователь «{user.full_name}» отклонен по причине «{reason.value}» ({update.effective_user.full_name})"
    )

    await update.callback_query.edit_message_reply_markup(reply_markup=None)

    return None
