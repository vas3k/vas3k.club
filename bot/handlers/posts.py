import logging

import telegram
from django.urls import reverse
from telegram import Update
from telegram.ext import CallbackContext

from bot.handlers.common import get_club_user
from club import settings
from notifications.telegram.common import send_telegram_message, Chat
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription

log = logging.getLogger(__name__)


def subscribe(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user or not user.telegram_id:
        return None

    _, post_id = update.callback_query.data.split(":", 1)
    post = Post.objects.filter(id=post_id).first()
    if not post:
        return None

    _, is_created = PostSubscription.subscribe(
        user=user,
        post=post,
        type=PostSubscription.TYPE_TOP_LEVEL_ONLY,
    )

    if user.telegram_id:
        post_url = settings.APP_HOST + reverse("show_post", kwargs={
            "post_type": post.type,
            "post_slug": post.slug,
        })

        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"➜ Вы подписались на уведомления о новых комментариях "
                 f"к посту «<a href=\"{post_url}\">{post.title}</a>» 🔔\n\n"
                 f"Они будут приходить сюда в бота.",
            parse_mode=telegram.ParseMode.HTML,
        )


def unsubscribe(update: Update, context: CallbackContext) -> None:
    user = get_club_user(update)
    if not user or not user.telegram_id:
        return None

    _, post_id = update.callback_query.data.split(":", 1)
    post = Post.objects.filter(id=post_id).first()
    if not post:
        return None

    is_unsubscribed = PostSubscription.unsubscribe(
        user=user,
        post=post,
    )

    if user.telegram_id:
        post_url = settings.APP_HOST + reverse("show_post", kwargs={
            "post_type": post.type,
            "post_slug": post.slug,
        })

        if is_unsubscribed:
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=f"➜ Вы отписались от о комментариев к посту «<a href=\"{post_url}\">{post.title}</a>» 🔕\n\n"
                     f"Однако, люди всё еще могут пингануть вас по имени.",
                parse_mode=telegram.ParseMode.HTML,
            )
        else:
            send_telegram_message(
                chat=Chat(id=user.telegram_id),
                text=f"➜ Вы и так не подписаны на пост «<a href=\"{post_url}\">{post.title}</a>». "
                     f"Скорее всего кто-то упомянул вас по имени.",
                parse_mode=telegram.ParseMode.HTML,
            )
