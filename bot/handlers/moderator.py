from datetime import datetime

from django.conf import settings
from django.urls import reverse
from telegram import Update

from bot.common import send_telegram_message, ADMIN_CHAT, remove_action_buttons
from notifications.email.users import send_welcome_drink
from notifications.telegram.posts import notify_post_author_approved, notify_post_author_rejected
from notifications.telegram.users import notify_user_profile_approved, notify_user_profile_rejected
from posts.models import Post
from users.models import User


def process_moderator_actions(update):
    # find an action processor
    action_name, entity_id = update.callback_query.data.split(":", 1)
    action = ACTIONS.get(action_name)

    if not action:
        send_telegram_message(
            chat=ADMIN_CHAT,
            text=f"😱 Неизвестная команда '{update.callback_query.data}'"
        )

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
    post.is_approved_by_moderator = True
    post.last_activity_at = datetime.utcnow()
    post.save()

    notify_post_author_approved(post)

    announce_post_url = settings.APP_HOST + reverse("announce_post", kwargs={
        "post_slug": post.slug,
    })

    return f"👍 Пост «{post.title}» одобрен ({update.effective_user.full_name}). " \
           f"Можно запостить его на канал вот здесь: {announce_post_url}", True


def forgive_post(post_id: str, update: Update) -> (str, bool):
    post = Post.objects.get(id=post_id)
    post.is_approved_by_moderator = False
    post.save()

    return f"😕 Пост «{post.title}» не одобрен, но оставлен на сайте ({update.effective_user.full_name})", True


def unpublish_post(post_id: str, update: Update) -> (str, bool):
    post = Post.objects.get(id=post_id)
    post.is_visible = False
    post.save()

    notify_post_author_rejected(post)

    return f"👎 Пост «{post.title}» перенесен в черновики ({update.effective_user.full_name})", True


def approve_user_profile(user_id: str, update: Update) -> (str, bool):
    user = User.objects.get(id=user_id)
    if user.is_profile_reviewed and user.is_profile_complete:
        return f"Пользователь «{user.full_name}» уже одобрен", True

    user.is_profile_complete = True
    user.is_profile_reviewed = True
    user.is_profile_rejected = False
    user.save()

    # make intro visible
    Post.objects\
        .filter(author=user, type=Post.TYPE_INTRO)\
        .update(is_visible=True, is_approved_by_moderator=True)

    notify_user_profile_approved(user)
    send_welcome_drink(user)

    return f"✅ Пользователь «{user.full_name}» одобрен ({update.effective_user.full_name})", True


def reject_user_profile(user_id: str, update: Update) -> (str, bool):
    user = User.objects.get(id=user_id)
    user.is_profile_complete = True
    user.is_profile_reviewed = True
    user.is_profile_rejected = True
    user.save()

    notify_user_profile_rejected(user)

    return f"❌ Пользователь «{user.full_name}» отклонен ({update.effective_user.full_name})", True


ACTIONS = {
    "approve_post": approve_post,
    "forgive_post": forgive_post,
    "delete_post": unpublish_post,
    "approve_user": approve_user_profile,
    "reject_user": reject_user_profile,
}
