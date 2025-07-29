from collections import namedtuple

import telegram
from django.conf import settings
from django.template import loader
from telegram import ParseMode

from common.regexp import IMAGE_RE
from notifications.telegram.bot import bot, log

Chat = namedtuple("Chat", ["id"])

ADMIN_CHAT = Chat(id=settings.TELEGRAM_ADMIN_CHAT_ID)
CLUB_CHAT = Chat(id=settings.TELEGRAM_CLUB_CHAT_ID)
CLUB_CHANNEL = Chat(id=settings.TELEGRAM_CLUB_CHANNEL_ID)
CLUB_ONLINE = Chat(id=settings.TELEGRAM_ONLINE_CHANNEL_ID)

NORMAL_TEXT_LIMIT = 4096
PHOTO_TEXT_LIMIT = 1024


def send_telegram_message(
    chat: Chat,
    text: str,
    parse_mode: ParseMode = telegram.ParseMode.HTML,
    disable_preview: bool = True,
    **kwargs
):
    if not bot:
        log.warning("No telegram token. Skipping")
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
                **kwargs
            )
        else:
            return bot.send_message(
                chat_id=chat.id,
                text=text[:NORMAL_TEXT_LIMIT],
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview,
                **kwargs
            )
    except telegram.error.TelegramError as ex:
        log.warning(f"Telegram error: {ex}")


def send_telegram_image(
    chat: Chat,
    image_url: str,
    text: str,
    parse_mode: ParseMode = telegram.ParseMode.HTML,
    **kwargs
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
            **kwargs
        )
    except telegram.error.TelegramError as ex:
        log.warning(f"Telegram error: {ex}")


def remove_action_buttons(chat: Chat, message_id: str, **kwargs):
    try:
        return bot.edit_message_reply_markup(
            chat_id=chat.id,
            message_id=message_id,
            reply_markup=None,
            **kwargs
        )
    except telegram.error.TelegramError:
        log.info("Buttons are already removed. Skipping")
        return None


def render_html_message(template, **data):
    template = loader.get_template(f"messages/{template}")
    return template.render({
        **data,
        "settings": settings
    })
