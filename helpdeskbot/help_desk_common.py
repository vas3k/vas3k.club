from telegram import Bot, ParseMode, Update, ReplyMarkup

from club import settings


def send_msg(chat_id: int,
             text: str,
             reply_to_message_id: int = None,
             parse_mode: ParseMode = ParseMode.HTML
             ):
    bot = Bot(token=settings.TELEGRAM_HELP_DESK_BOT_TOKEN)
    return bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id, parse_mode=parse_mode)


def msg_reply(update: Update,
              text: str,
              parse_mode: ParseMode = ParseMode.HTML,
              reply_markup: ReplyMarkup = None,
              disable_web_page_preview: bool = True,
              ):
    update.message.reply_text(
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        disable_web_page_preview=disable_web_page_preview
    )


def channel_msg_link(message_id: str) -> str:
    channel_link_id = str(settings.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID).replace("-100", "")
    return chat_msg_link(channel_link_id, message_id)


def chat_msg_link(chat_id: str, message_id: str) -> str:
    return f"https://t.me/c/{chat_id}/{message_id}"
