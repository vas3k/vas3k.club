import logging

from django.urls import reverse
from telegram import Update
from telegram.ext import CallbackContext

from bot.handlers.common import get_club_user
from club import settings
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
        update.callback_query.answer(
            text=f"Вы подписались на уведомления о новых комментариях к посту «{post.title}» 🔔"
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
            update.callback_query.answer(
                text=f"Вы отписались от о комментариев к посту «{post.title}» 🔕"
            )
        else:
            update.callback_query.answer(
                text="Вы и не были подписаны на уведомления к этому посту ❌"
            )
