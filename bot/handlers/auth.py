from telegram import Update, ParseMode
from telegram.error import Unauthorized
from telegram.ext import CallbackContext

from bot.cache import flush_users_cache, cached_telegram_users
from users.models.user import User


def command_auth(update: Update, context: CallbackContext) -> None:
    if not update.message or not update.message.text or " " not in update.message.text:
        update.effective_chat.send_message(
            "☝️ Нужно прислать мне секретный код. "
            "Напиши /auth и код из <a href=\"https://vas3k.club/user/me/edit/bot/\">профиля в Клубе</a> "
            "через пробел. Только не публикуй его в публичных чатах!",
            parse_mode=ParseMode.HTML
        )
        return None

    secret_code = update.message.text.split(" ", 1)[1].strip()
    user = User.objects.filter(secret_hash=secret_code).first()

    if not user:
        update.effective_chat.send_message("Пользователь с таким кодом не найден")
        return None

    user.telegram_id = update.effective_user.id
    user.telegram_data = {
        "id": update.effective_user.id,
        "username": update.effective_user.username,
        "first_name": update.effective_user.first_name,
        "last_name": update.effective_user.last_name,
        "language_code": update.effective_user.language_code,
    }
    user.save()

    try:
        update.effective_chat.send_message(f"Отличный код! Приятно познакомиться, {user.slug}")
    except Unauthorized:
        return None

    update.message.delete()

    if user.moderation_status != User.MODERATION_STATUS_APPROVED:
        update.effective_chat.send_message(f"Теперь осталось пройти модерацию. Бот заработает сразу после этого")

    # Refresh the cache by deleting and requesting it again
    flush_users_cache()
    cached_telegram_users()

    return None
