from django.urls import reverse
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from bot.decorators import is_club_member
from club import settings
from users.models.user import User


@is_club_member
def command_whois(update: Update, context: CallbackContext) -> None:
    if not update.message or not update.message.reply_to_message:
        update.effective_chat.send_message(
            "Эту команду нужно вызывать реплаем на сообщение человека, о котором вы хотите узнать",
            quote=True
        )
        return None

    if update.message.reply_to_message.from_user.is_bot:
        update.message.reply_text(
            "Это бот, глупышка",
            quote=True
        )
        return None

    telegram_id = update.message.reply_to_message.from_user.id
    user = User.objects.filter(telegram_id=telegram_id).first()
    if not user:
        update.message.reply_text(
            f"🤨 Пользователь не найден в Клубе. Гоните его, надсмехайтесь над ним!",
            quote=True
        )
        return None

    profile_url = settings.APP_HOST + reverse("profile", kwargs={
        "user_slug": user.slug,
    })

    update.message.reply_text(
        f"""Кажется, это <a href="{profile_url}">{user.full_name}</a>""",
        parse_mode=ParseMode.HTML,
        quote=True
    )

    return None
