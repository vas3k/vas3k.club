from django.conf import settings
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from bot.cache import cached_telegram_users
from users.models.user import User


def is_moderator(callback):
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if update.effective_chat.id != int(settings.TELEGRAM_ADMIN_CHAT_ID):
            update.effective_chat.send_message("❌ Для этого действия нужно быть в чате модераторов")
            return None

        moderator = User.objects.filter(telegram_id=update.effective_user.id).first()
        if not moderator or not moderator.is_moderator:
            update.effective_chat.send_message(
                f"⚠️ '{update.effective_user.full_name}' не модератор или не привязал бота к аккаунту"
            )
            return None

        return callback(update, context, *args, **kwargs)

    return wrapper


def is_club_member(callback):
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        club_users = cached_telegram_users()

        if str(update.effective_user.id) not in set(club_users):
            if update.callback_query:
                update.callback_query.answer(text=f"☝️ Привяжи бота к профилю, братишка")
            else:
                update.message.reply_text(
                    f"☝️ Привяжи <a href=\"https://vas3k.club/user/me/edit/bot/\">бота</a> к профилю, братишка",
                    parse_mode=ParseMode.HTML
                )
            return None

        return callback(update, context, *args, **kwargs)

    return wrapper
