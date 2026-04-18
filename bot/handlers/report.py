import html

from django.conf import settings
from django.urls import reverse

from telegram import Update, ParseMode
from telegram import Chat as TGChat
from telegram.ext import CallbackContext

from bot.decorators import is_club_member, ensure_fresh_db_connection
from users.models.user import User
from rooms.models import Room


@is_club_member
@ensure_fresh_db_connection
def command_report(update: Update, context: CallbackContext) -> None:
    message = update.message

    if not message:
        return None

    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    comment = parts[1].strip() if len(parts) > 1 else ""

    reply = message.reply_to_message

    # Validate input
    if not reply and not comment:
        message.reply_text(
            "Нужно либо ответить на сообщение с комментарием (/report спам), либо написать /report текст",
            quote=True
        )
        return None

    # Reporter
    reporter_tg = message.from_user
    reporter = User.objects.filter(telegram_id=reporter_tg.id).first()

    reporter_text = f"{html.escape(reporter_tg.full_name)}"
    if reporter_tg.username:
        reporter_text += f" (@{reporter_tg.username})"

    if reporter:
        profile_url = settings.APP_HOST + reverse("profile", kwargs={
            "user_slug": reporter.slug,
        })
        reporter_text = f'<a href="{profile_url}">{reporter_text}</a>'

    # Chat info
    chat = message.chat
    chat_title = chat.title or chat.full_name or "Личные сообщения"

    room = None
    if chat.type != TGChat.PRIVATE:
        room = Room.objects.filter(telegram_chat_id=chat.id).first()

    if chat.type == TGChat.PRIVATE:
        chat_text = "Репорт из бота"
    else:
        chat_text = html.escape(chat_title)
        if room:
            room_url = settings.APP_HOST + reverse("room", kwargs={
                "room_slug": room.slug,
            })
            chat_text = f'<a href="{room_url}">{chat_text}</a>'

    # Reported user
    reported_text = "Неизвестно"
    replied_message_text = ""

    if reply:
        original = reply
        from_user = original.from_user

        if from_user:
            reported_user = User.objects.filter(telegram_id=from_user.id).first()

            reported_text = f"{html.escape(from_user.full_name)}"
            if from_user.username:
                reported_text += f" (@{from_user.username})"
            reported_text += f" [id={from_user.id}]"

            if reported_user:
                profile_url = settings.APP_HOST + reverse("profile", kwargs={
                    "user_slug": reported_user.slug,
                })
                reported_text = f'<a href="{profile_url}">{reported_text}</a>'
            else:
                reported_text += " — Юзер не из Клуба"

        # Message content
        if original.text:
            replied_message_text = html.escape(original.text)
        elif original.caption:
            replied_message_text = html.escape(original.caption)
        else:
            replied_message_text = "[медиа/не текст]"

    # Build final message
    report_text = f"""
🚨 <b>Новый репорт</b>

<b>Чат:</b> {chat_text}
<b>Отправитель репорта:</b> {reporter_text}
"""

    if reply:
        report_text += f"<b>На кого:</b> {reported_text}\n"
        report_text += f"<b>Сообщение:</b>\n<blockquote>{replied_message_text}</blockquote>\n"

    if comment:
        report_text += f"<b>Комментарий:</b>\n{html.escape(comment)}\n"

    # Send to admin chat
    context.bot.send_message(
        chat_id=settings.TELEGRAM_ADMIN_CHAT_ID,
        text=report_text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

    message.reply_text(
        "Спасибо, репорт отправлен 👍",
        quote=True
    )

    return None