import html

from django.urls import reverse
from telegram import Chat as TGChat, MessageOrigin, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from bot.decorators import is_club_member, ensure_fresh_db_connection
from club import settings
from users.models.user import User


@ensure_fresh_db_connection
@is_club_member
async def command_whois(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return None
          
    message = update.message
    is_private_forward = message is not None \
        and message.forward_date is not None \
        and message.chat.type == TGChat.PRIVATE

    # If there is no reply/forward – try `/whois <telegram_username>` using the raw message text
    if not message or (not message.reply_to_message and not is_private_forward):
        text = (message.text or "").strip() if message else ""
        parts = text.split(maxsplit=1)

        if len(parts) < 2:
            await update.effective_chat.send_message(
                "Эту команду нужно вызывать реплаем на сообщение человека, о котором вы хотите узнать "
                "или в формате /whois @username",
                quote=True
            )
            return None

        telegram_nick_or_id = parts[1].strip()
        if not telegram_nick_or_id:
            await update.effective_chat.send_message(
                "Эту команду нужно вызывать реплаем на сообщение человека, о котором вы хотите узнать "
                "или в формате /whois @username",
                quote=True
            )
            return None

        # If argument is a number – treat it as telegram_id, otherwise as @username
        if telegram_nick_or_id.isdigit():
            user = User.objects.filter(telegram_id=telegram_nick_or_id).first()
        else:
            username = telegram_nick_or_id.lstrip("@").strip()
            if not username:
                await update.effective_chat.send_message(
                    "Эту команду нужно вызывать реплаем на сообщение человека, о котором вы хотите узнать "
                    "или в формате /whois @username",
                    quote=True
                )
                return None
            user = User.objects.filter(telegram_id__isnull=False, telegram_data__username__iexact=username).first()

        if not user:
            await update.effective_chat.send_message(
                "🤨 Пользователь с таким телеграм-никнеймом или ID не найден в Клубе.",
                quote=True
            )
            return None

        profile_url = settings.APP_HOST + reverse("profile", kwargs={
            "user_slug": user.slug,
        })

        await message.reply_text(
            f"""Кажется, это <a href="{profile_url}">{html.escape(user.full_name)}</a>""",
            parse_mode=ParseMode.HTML,
            quote=True
        )
        return None

    original_message = message  # look at the author of this message (works only in private chats)
    if message.reply_to_message:
        original_message = message.reply_to_message  # look at the author of replied message

    from_user = original_message.from_user
    origin = original_message.forward_origin
    if origin is not None:
        if origin.type == MessageOrigin.HIDDEN_USER:
            await update.message.reply_text(
                f"🤨 Кажется, {origin.sender_user_name} скрыл свой профиль для пересылаемых сообщений. Попробуй дать команду в ответ на исходное сообщение",
                do_quote=True,
            )
            return None
        if origin.type == MessageOrigin.USER:
            from_user = origin.sender_user

    if from_user.is_bot:
        if getattr(original_message, 'sender_chat', None):
            await update.message.reply_text(
                "Сообщение отправлено от имени чата/канала",
                do_quote=True
            )
            return
        await update.message.reply_text(
            "Это бот, глупышка",
            do_quote=True
        )
        return None

    telegram_id = from_user.id
    user = User.objects.filter(telegram_id=telegram_id).first()
    if not user:
        await update.message.reply_text(
            f"🤨 Пользователь не найден в Клубе. Гоните его, насмехайтесь над ним!",
            do_quote=True
        )
        return None

    profile_url = settings.APP_HOST + reverse("profile", kwargs={
        "user_slug": user.slug,
    })

    await update.message.reply_text(
        f"""Кажется, это <a href="{profile_url}">{html.escape(user.full_name)}</a>""",
        parse_mode=ParseMode.HTML,
        do_quote=True
    )

    return None
