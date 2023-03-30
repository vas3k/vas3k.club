from django.urls import reverse
from telegram import Update, ParseMode
from telegram import Chat as TGChat
from telegram.ext import CallbackContext

from bot.decorators import is_club_member
from club import settings
from users.models.user import User


@is_club_member
def command_whois(update: Update, context: CallbackContext) -> None:
    is_private_forward = update.message is not None \
        and update.message.forward_date is not None \
        and update.message.chat.type == TGChat.PRIVATE

    if not update.message or not update.message.reply_to_message and not is_private_forward:
        update.effective_chat.send_message(
            "Эту команду нужно вызывать реплаем на сообщение человека, о котором вы хотите узнать",
            quote=True
        )
        return None

    original_message = update.message  # look at the author of this message (works only in private chats)
    if update.message.reply_to_message:
        original_message = update.message.reply_to_message  # look at the author of replied message

    from_user = original_message.from_user
    if original_message.forward_date:
        if not original_message.forward_from:
            update.effective_chat.send_message(
                f"🤨 Кажется, {original_message.forward_sender_name} скрыл свой профиль для пересылаемых сообщений. Попробуй дать команду в ответ на исходное сообщение",
                quote=True
            )
            return None
        from_user = original_message.forward_from

    if from_user.is_bot:
        if getattr(original_message, 'sender_chat', None):
            update.message.reply_text(
                "Сообщение отправлено от имени чата/канала",
                quote=True
            )
            return
        update.message.reply_text(
            "Это бот, глупышка",
            quote=True
        )
        return None

    telegram_id = from_user.id
    user = User.objects.filter(telegram_id=telegram_id).first()
    if not user:
        update.message.reply_text(
            f"🤨 Пользователь не найден в Клубе. Гоните его, насмехайтесь над ним!",
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
