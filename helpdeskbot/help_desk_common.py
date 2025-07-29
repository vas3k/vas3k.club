from telegram import Bot, ParseMode, Update, ReplyMarkup

from helpdeskbot import config

bot = Bot(token=config.TELEGRAM_HELP_DESK_BOT_TOKEN)


def send_message(
    chat_id: int,
    text: str,
    reply_to_message_id: int = None,
    parse_mode: ParseMode = ParseMode.HTML,
    disable_web_page_preview=True
):
    return bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_to_message_id=reply_to_message_id,
        parse_mode=parse_mode,
        disable_web_page_preview=disable_web_page_preview,
    )


def edit_message(
    chat_id: int,
    message_id: int,
    new_text: str,
    parse_mode: ParseMode = ParseMode.HTML
):
    return bot.edit_message_text(text=new_text, chat_id=chat_id, message_id=message_id, parse_mode=parse_mode)


def send_reply(
    update: Update,
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


def get_channel_message_link(message_id: str) -> str:
    channel_link_id = str(config.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID).replace("-100", "")
    return get_chat_message_link(channel_link_id, message_id)


def get_chat_message_link(chat_id: str, message_id: str) -> str:
    return f"https://t.me/c/{chat_id}/{message_id}"
