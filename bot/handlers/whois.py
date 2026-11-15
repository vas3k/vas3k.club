from django.template.loader import render_to_string
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
        return

    message = update.message
    reply = message.reply_to_message

    # Ordinary reply chains also have thread IDs; only forum roots are implicit replies.
    if reply and message.is_topic_message and reply.id == message.message_thread_id:
        reply = None

    if message.chat.type == TGChat.PRIVATE and message.forward_origin:
        origin = message.forward_origin

        if origin.type == MessageOrigin.HIDDEN_USER:
            await message.reply_text(
                f"🤨 Кажется, {origin.sender_user_name} скрыл свой профиль для пересылаемых сообщений. "
                "Попробуй сделать whois в ответ на исходное сообщение в чате",
                do_quote=True,
            )
            return

        if origin.type != MessageOrigin.USER:
            await message.reply_text(
                "Сообщение отправлено от имени чата/канала",
                do_quote=True,
            )
            return

        from_user = origin.sender_user
    elif reply:
        if reply.sender_chat or reply.from_user is None:
            await message.reply_text(
                "Сообщение отправлено от имени чата/канала",
                do_quote=True,
            )
            return

        from_user = reply.from_user
    else:
        from_user = None

    if from_user is not None:
        if from_user.is_bot:
            await message.reply_text(
                "Это бот, глупышка",
                do_quote=True,
            )
            return

        user = User.objects.filter(telegram_id=from_user.id).first()
    else:
        parts = (message.text or "").split()
        target = parts[1].lstrip("@") if len(parts) == 2 else ""

        if not target:
            await message.reply_text(
                "Эту команду нужно вызывать реплаем на сообщение человека, о котором вы хотите узнать "
                "или в формате /whois @username или /whois telegram_id",
                do_quote=True,
            )
            return

        if target.isascii() and target.isdigit():
            user = User.objects.filter(telegram_id=target).first()
        else:
            user = User.objects.filter(telegram_id__isnull=False, telegram_data__username__iexact=target).first()

    if not user:
        await message.reply_text(
            "🤨 Пользователь не найден в Клубе. Гоните его, насмехайтесь над ним!"
            if from_user is not None else
            "🤨 Пользователь с таким телеграм-никнеймом или ID не найден в Клубе.",
            do_quote=True,
        )
        return

    profile_url = settings.APP_HOST + reverse("profile", kwargs={"user_slug": user.slug})
    await message.reply_text(
        render_to_string("notifications/telegram/membership/profile.html", {
            "user": user,
            "profile_url": profile_url,
        }).strip(),
        parse_mode=ParseMode.HTML,
        do_quote=True,
    )
