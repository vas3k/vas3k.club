from telegram import Update
from telegram.ext import CallbackContext

from ai.assistant import ask_assistant
from ai.rate_limiter import is_rate_limited
from bot.handlers.common import get_club_user
from common.markdown.markdown import markdown_tg


def ai_response(update: Update, context: CallbackContext) -> None:
    message_text = (
       update.message.reply_to_message.text or
       update.message.reply_to_message.caption or
       ""
    )
    if not message_text:
        return None

    user = get_club_user(update)
    if not user:
        update.message.reply_text("Я отвечаю только на вопросы членов Клуба")
        return None

    # send typing action
    context.bot.send_chat_action(update.effective_chat.id, "typing")

    if is_rate_limited("ai_bot"):
        update.message.reply_text("Чот я устал отвечать на вопросы... давай потом")
        return None

    answer = ask_assistant(message_text)
    if answer:
        update.effective_chat.send_message(markdown_tg("\n\n".join(answer)))

    return None
