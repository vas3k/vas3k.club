from __future__ import annotations

from typing import TYPE_CHECKING

from telegram import (
    ForceReply,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ReplyParameters,
    Update,
)
from telegram.constants import ParseMode

if TYPE_CHECKING:
    from telegram import Bot

from helpdeskbot import config


async def send_message(
    bot: Bot,
    chat_id: int,
    text: str,
    reply_to_message_id: int = None,
    parse_mode: str = ParseMode.HTML,
    disable_preview: bool = True,
):
    return await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_parameters=ReplyParameters(message_id=reply_to_message_id) if reply_to_message_id else None,
        parse_mode=parse_mode,
        link_preview_options=LinkPreviewOptions(is_disabled=disable_preview),
    )


async def edit_message(
    bot: Bot,
    chat_id: int,
    message_id: int,
    new_text: str,
    parse_mode: str = ParseMode.HTML
):
    return await bot.edit_message_text(text=new_text, chat_id=chat_id, message_id=message_id, parse_mode=parse_mode)


async def send_reply(
    update: Update,
    text: str,
    parse_mode: str = ParseMode.HTML,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | ReplyKeyboardRemove | ForceReply | None = None,
    disable_preview: bool = True,
):
    await update.message.reply_text(
        text=text,
        parse_mode=parse_mode,
        reply_markup=reply_markup,
        link_preview_options=LinkPreviewOptions(is_disabled=disable_preview),
    )


def get_channel_message_link(message_id: str) -> str:
    channel_link_id = str(config.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID).replace("-100", "")
    return get_chat_message_link(channel_link_id, message_id)


def get_chat_message_link(chat_id: str, message_id: str) -> str:
    return f"https://t.me/c/{chat_id}/{message_id}"
