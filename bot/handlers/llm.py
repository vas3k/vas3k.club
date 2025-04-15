from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from ai.assistant import ask_assistant
from ai.rate_limiter import is_rate_limited
from bot.handlers.common import get_club_user
from common.markdown.markdown import markdown_tg


def llm_response(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return None

    message_text = (
       update.message.text or
       update.message.caption or
       ""
    )
    if not message_text:
        return None

    # get reply context
    reply_to_text = ""
    if update.message.reply_to_message:
        reply_to_text = (
           update.message.reply_to_message.text or
           update.message.reply_to_message.caption or
           ""
        )

    # only club members can use the bot
    user = get_club_user(update)
    if not user or not user.is_active_member:
        update.message.reply_text(
            "🙈 Я отвечаю только чувакам с активной подпиской в Клубе. Иди продлевай! https://vas3k.club/user/me/",
            disable_web_page_preview=True
        )
        return None

    # send typing action
    context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if is_rate_limited("ai_bot"):
        update.message.reply_text("Чот я устал отвечать на вопросы... давай потом")
        return None

    user_input = [
        f"Я — {user.full_name}",
        message_text
    ]
    if reply_to_text:
        user_input = [f"Предыдущее сообщение: {reply_to_text}"] + user_input

    answer = ask_assistant("\n".join(user_input))
    if answer:
        update.message.reply_text(
            markdown_tg("\n\n".join(answer)),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    return None
