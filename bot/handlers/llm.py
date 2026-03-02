from telegram import LinkPreviewOptions, Update
from telegram.constants import ParseMode
from telegram.ext import CallbackContext

from ai.assistant import ask_assistant
from ai.rate_limiter import is_rate_limited
from bot.decorators import ensure_fresh_db_connection
from bot.handlers.common import get_club_user
from common.markdown.markdown import markdown_tg


@ensure_fresh_db_connection
async def llm_response(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return None

    message_text = (
       update.message.text or
       update.message.caption or
       ""
    )
    if not message_text:
        return None

    reply_to_text = ""
    if update.message.reply_to_message:
        reply_to_text = (
           update.message.reply_to_message.text or
           update.message.reply_to_message.caption or
           ""
        )

    user = await get_club_user(update)
    if not user:
        return None

    if not user.is_active_member:
        await update.message.reply_text(
            "🙈 Я отвечаю только чувакам с активной подпиской в Клубе. Иди продлевай! https://vas3k.club/user/me/",
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )
        return None

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if is_rate_limited("ai_bot"):
        await update.message.reply_text("Чот я устал отвечать на вопросы... давай потом")
        return None

    user_input = [
        f"Я — {user.full_name} {user.slug}",
        message_text
    ]
    if reply_to_text:
        user_input = [f"Предыдущее сообщение: {reply_to_text}"] + user_input

    answer = ask_assistant("\n".join(user_input))
    if answer:
        await update.message.reply_text(
            markdown_tg(answer),
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(is_disabled=True)
        )

    return None
