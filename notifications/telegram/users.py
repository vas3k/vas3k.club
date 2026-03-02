from django.conf import settings
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from django.template import TemplateDoesNotExist
from django.urls import reverse

from ai.moderation import ai_rate_intro_quality
from notifications.telegram.common import Chat, ADMIN_CHAT, send_telegram_message, render_html_message
from bot.handlers.common import UserRejectReason
from users.models.user import User


def notify_profile_needs_review(user, intro):
    admin_profile_url = settings.APP_HOST + reverse("godmode_action", kwargs={
        "model_name": "users",
        "item_id": user.id,
        "action_code": "message"
    })

    message = send_telegram_message(
        chat=ADMIN_CHAT,
        text=render_html_message("moderator_new_member_review.html", user=user, intro=intro),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍 Впустить", callback_data=f"approve_user:{user.id}")
            ],
            [
                InlineKeyboardButton("❌️ Плохое интро", callback_data=f"reject_user_intro:{user.id}"),
            ],
            [
                InlineKeyboardButton("❌️ Плохое имя", callback_data=f"reject_user_name:{user.id}"),
            ],
            [
                InlineKeyboardButton("❌️ Слишком общее", callback_data=f"reject_user_general:{user.id}"),
            ],
            [
                InlineKeyboardButton("❌️ Нет контактов", callback_data=f"reject_user_data:{user.id}"),
            ],
            [
                InlineKeyboardButton("❌️ ИИ-слоп", callback_data=f"reject_user_ai:{user.id}"),
            ],
            [
                InlineKeyboardButton("❌️ Агрессия", callback_data=f"reject_user_aggression:{user.id}"),
            ],
            [
                InlineKeyboardButton("✏️ Написать юзеру", url=admin_profile_url),
            ]
        ])
    )

    ai_intro_rate_text = ai_rate_intro_quality(user, intro)
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=ai_intro_rate_text,
        parse_mode=ParseMode.HTML,
        reply_to_message_id=message.message_id,
    )


def notify_user_profile_approved(user):
    user_profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user.slug})

    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"🚀 Поздравляем, вы прошли модерацию. Добро пожаловать в Клуб!"
                 f"\n\nТеперь можно пойти заполнять другие смешные поля в своем профиле, "
                 f"указать хобби, добавить картинок в интро и просто сделать его красивым:"
                 f"\n\n{user_profile_url}"
        )


def notify_user_profile_rejected(user: User, reason: UserRejectReason):
    try:
        text = render_html_message(f"rejected/{reason.value}.html", user=user)
    except TemplateDoesNotExist:
        text = render_html_message(f"rejected/intro.html", user=user)

    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=text,
        )


def notify_user_ping(user, message):
    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"👋 <b>Вам письмо от модераторов Клуба:</b> {message}"
        )


def notify_admin_user_ping(user, message):
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=f"🛎 <b>Юзера {user.slug} пинганули:</b> {message}"
    )


def notify_admin_user_unmoderate(user):
    send_telegram_message(
        chat=ADMIN_CHAT,
        text=f"💣 <b>Юзера {user.slug} размодерировали</b>"
    )


def notify_user_auth(user, code):
    if user.telegram_id:
        send_telegram_message(
            chat=Chat(id=user.telegram_id),
            text=f"<code>{code.code}</code> — ваш одноразовый код для входа в Клуб",
        )
