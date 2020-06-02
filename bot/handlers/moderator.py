from datetime import datetime

from django.conf import settings
from django.urls import reverse
from telegram import Update

from bot.common import send_telegram_message, ADMIN_CHAT, remove_action_buttons
from notifications.email.users import send_welcome_drink, send_rejected_email
from notifications.telegram.posts import notify_post_author_approved, notify_post_author_rejected, announce_in_club_chats
from notifications.telegram.users import notify_user_profile_approved, notify_user_profile_rejected
from posts.models import Post
from search.models import SearchIndex
from users.models.user import User


def process_moderator_actions(update):
    # find an action processor
    action_name, entity_id = update.callback_query.data.split(":", 1)
    action = ACTIONS.get(action_name)

    moderator = User.objects.filter(telegram_id=update.effective_user.id).first()
    if not moderator or not moderator.is_moderator:
        send_telegram_message(
            chat=ADMIN_CHAT,
            text=f"⚠️ '{update.effective_user.full_name}' не модератор или не привязал бота к аккаунту"
        )
        return

    if not action:
        send_telegram_message(
            chat=ADMIN_CHAT,
            text=f"😱 Неизвестная команда '{update.callback_query.data}'"
        )
        return

    # run run run
    try:
        result, is_final = action(entity_id, update)
    except Exception as ex:
        send_telegram_message(
            chat=ADMIN_CHAT,
            text=f"❌ Экшен наебнулся '{update.callback_query.data}': {ex}"
        )
        return

    # send results back to the chat
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=result
    )

    # hide admin buttons (to not allow people do the same thing twice)
    if is_final:
        remove_action_buttons(
            chat=ADMIN_CHAT,
            message_id=update.effective_message.message_id,
        )

    return result


def approve_post(post_id: str, update: Update) -> (str, bool):
    post = Post.objects.get(id=post_id)
    if post.is_approved_by_moderator:
        return f"Пост «{post.title}» уже одобрен", True

    post.is_approved_by_moderator = True
    post.last_activity_at = datetime.utcnow()
    post.published_at = datetime.utcnow()
    post.save()

    notify_post_author_approved(post)
    announce_in_club_chats(post)

    announce_post_url = settings.APP_HOST + reverse("announce_post", kwargs={
        "post_slug": post.slug,
    })

    return f"👍 Пост «{post.title}» одобрен ({update.effective_user.full_name}). " \
           f"Можно запостить его на канал вот здесь: {announce_post_url}", True


def forgive_post(post_id: str, update: Update) -> (str, bool):
    post = Post.objects.get(id=post_id)
    post.is_approved_by_moderator = False
    post.published_at = datetime.utcnow()
    post.save()

    return f"😕 Пост «{post.title}» не одобрен, но оставлен на сайте ({update.effective_user.full_name})", True


def unpublish_post(post_id: str, update: Update) -> (str, bool):
    post = Post.objects.get(id=post_id)
    if not post.is_visible:
        return f"Пост «{post.title}» уже перенесен в черновики", True

    post.is_visible = False
    post.save()

    SearchIndex.update_post_index(post)

    notify_post_author_rejected(post)

    return f"👎 Пост «{post.title}» перенесен в черновики ({update.effective_user.full_name})", True


def approve_user_profile(user_id: str, update: Update) -> (str, bool):
    user = User.objects.get(id=user_id)
    if user.moderation_status == User.MODERATION_STATUS_APPROVED:
        return f"Пользователь «{user.full_name}» уже одобрен", True

    if user.moderation_status == User.MODERATION_STATUS_REJECTED:
        return f"Пользователь «{user.full_name}» уже отклонен", True

    user.moderation_status = User.MODERATION_STATUS_APPROVED
    user.save()

    # make intro visible
    Post.objects\
        .filter(author=user, type=Post.TYPE_INTRO)\
        .update(is_visible=True, published_at=datetime.utcnow(), is_approved_by_moderator=True)

    SearchIndex.update_user_index(user)

    notify_user_profile_approved(user)
    send_welcome_drink(user)

    return f"✅ Пользователь «{user.full_name}» одобрен ({update.effective_user.full_name})", True


def reject_user_profile(user_id: str, update: Update) -> (str, bool):
    user = User.objects.get(id=user_id)
    if user.moderation_status == User.MODERATION_STATUS_REJECTED:
        return f"Пользователь «{user.full_name}» уже был отклонен и пошел все переделывать", True

    user.moderation_status = User.MODERATION_STATUS_REJECTED
    user.save()

    notify_user_profile_rejected(user)
    send_rejected_email(user)

    return f"❌ Пользователь «{user.full_name}» отклонен ({update.effective_user.full_name})", True


ACTIONS = {
    "approve_post": approve_post,
    "forgive_post": forgive_post,
    "delete_post": unpublish_post,
    "approve_user": approve_user_profile,
    "reject_user": reject_user_profile,
}
