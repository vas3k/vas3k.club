import asyncio

from django.conf import settings
from django.db import close_old_connections, connections
from telegram import LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from ai.assistant import ask_assistant
from ai.rate_limiter import is_rate_limited, can_notify_ai_limit
from bot.decorators import ensure_fresh_db_connection
from bot.handlers.common import get_club_user
from common.markdown.markdown import markdown_tg
from rooms.models import Room


def _ask_assistant_with_db_connection(user_input: str, **context) -> str:
    # asyncio.to_thread() owns a separate Django connection. The async handler
    # cannot clean it up from the event-loop thread.
    try:
        close_old_connections()
        return ask_assistant(user_input, **context)
    finally:
        # Release it after every job, including when the assistant catches a DB error.
        # With pooling enabled, this returns the connection to the pool.
        connections.close_all()


@ensure_fresh_db_connection
async def llm_response(update: Update, context: CallbackContext) -> None:
    if not all((update.message, update.effective_user)):
        return None

    if any((update.effective_user.is_bot, update.message.sender_chat)):
        return None

    if not is_club_ai_chat(update.effective_chat):
        return None

    message_text = update.message.text or update.message.caption or ""
    if not message_text:
        return None

    reply_to_text = ""
    reply_is_bot = False
    if update.message.reply_to_message:
        reply = update.message.reply_to_message
        reply_to_text = reply.text or reply.caption or ""

        reply_author = update.message.reply_to_message.from_user
        reply_is_bot = bool(reply_author and reply_author.id == context.bot.id)

    user = await get_club_user(update)
    if not user:
        return None

    if not user.is_active_member:
        await update.message.reply_text(
            "🙈 Я отвечаю только чувакам с активной подпиской в Клубе. Иди продлевай! https://vas3k.club/user/me/",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return None

    if await asyncio.to_thread(is_rate_limited, str(user.id)):
        if await asyncio.to_thread(can_notify_ai_limit, str(user.id)):
            await update.message.reply_text("Чот я устал отвечать на вопросы... давай потом")
        return None

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        answer = await asyncio.to_thread(
            _ask_assistant_with_db_connection,
            message_text,
            reply_to_text=reply_to_text,
            reply_is_bot=reply_is_bot,
            user_name=f"{user.full_name} ({user.slug})",
        )
    except Exception:
        await update.message.reply_text("Что-то сломалось, попробуй ещё раз позже 🤷")
        return None

    if answer:
        await update.message.reply_text(
            markdown_tg(answer),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

    return None


def is_club_ai_chat(chat):
    if chat.type == "private":
        return True

    club_chats = {
        str(settings.TELEGRAM_CLUB_CHAT_ID), str(settings.TELEGRAM_ADMIN_CHAT_ID),
        str(settings.TELEGRAM_VIBES_CHAT_ID), str(settings.TELEGRAM_PARLIAMENT_CHAT_ID),
    }

    if str(chat.id) in club_chats:
        return True

    return Room.objects.filter(chat_id=str(chat.id)).exists()
