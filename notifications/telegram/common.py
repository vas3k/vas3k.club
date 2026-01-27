from collections import namedtuple

import telegram
from django.conf import settings
from django.template import loader

from common.regexp import IMAGE_RE
from notifications.telegram.bot import bot, log

Chat = namedtuple("Chat", ["id"])

ADMIN_CHAT = Chat(id=settings.TELEGRAM_ADMIN_CHAT_ID) if settings.TELEGRAM_ADMIN_CHAT_ID else None
CLUB_CHAT = Chat(id=settings.TELEGRAM_CLUB_CHAT_ID) if settings.TELEGRAM_CLUB_CHAT_ID else None
CLUB_CHANNEL = Chat(id=settings.TELEGRAM_CLUB_CHANNEL_ID) if settings.TELEGRAM_CLUB_CHANNEL_ID else None
CLUB_ONLINE = Chat(id=settings.TELEGRAM_ONLINE_CHANNEL_ID) if settings.TELEGRAM_ONLINE_CHANNEL_ID else None
VIBES_CHAT = Chat(id=settings.TELEGRAM_VIBES_CHAT_ID) if settings.TELEGRAM_VIBES_CHAT_ID else None
PARLIAMENT_CHAT = Chat(id=settings.TELEGRAM_PARLIAMENT_CHAT_ID) if settings.TELEGRAM_PARLIAMENT_CHAT_ID else None

NORMAL_TEXT_LIMIT = 4096
PHOTO_TEXT_LIMIT = 1024


def send_telegram_message(
    chat: Chat,
    text: str,
    parse_mode: str = telegram.ParseMode.HTML,
    reply_markup: telegram.InlineKeyboardMarkup | None = None,
    reply_to_message_id: int | None = None,
    disable_preview: bool = True,
):
    if not bot:
        log.warning("No telegram token. Skipping")
        return

    if not chat:
        log.warning("No chat id. Skipping")
        return

    log.info(f"Telegram: sending message to chat_id {chat.id}, starting with {text[:10]}...")

    images_in_message = IMAGE_RE.findall(text)

    try:
        if len(images_in_message) == 1 and len(text) < PHOTO_TEXT_LIMIT:
            return bot.send_photo(
                chat_id=chat.id,
                photo=images_in_message[0],
                caption=text[:PHOTO_TEXT_LIMIT],
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
            )
        else:
            return bot.send_message(
                chat_id=chat.id,
                text=text[:NORMAL_TEXT_LIMIT],
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
            )
    except telegram.error.TelegramError as ex:
        log.warning(f"Telegram error: {ex}")


def send_telegram_image(
    chat: Chat,
    image_url: str,
    text: str,
    parse_mode: str = telegram.ParseMode.HTML,
):
    if not bot:
        log.warning("No telegram token. Skipping")
        return

    log.info(f"Telegram: sending the image: {image_url} {text[:20]}")

    try:
        return bot.send_photo(
            chat_id=chat.id,
            photo=image_url,
            caption=text[:PHOTO_TEXT_LIMIT],
            parse_mode=parse_mode,
        )
    except telegram.error.TelegramError as ex:
        log.warning(f"Telegram error: {ex}")


def render_html_message(template, **data):
    template = loader.get_template(f"messages/{template}")
    return template.render({
        **data,
        "settings": settings
    })
