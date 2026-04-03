import logging

from telegram import Update, MessageOrigin
from telegram.ext import CallbackContext

from bot.decorators import ensure_fresh_db_connection
from helpdeskbot import config
from helpdeskbot.help_desk_common import get_channel_message_link, send_message
from helpdeskbot.models import Question, Answer
from helpdeskbot.room import get_rooms
from notifications.telegram.common import render_html_message

log = logging.getLogger(__name__)

rooms = {r.chat_id: r for r in get_rooms()}


@ensure_fresh_db_connection
async def on_reply_message(update: Update, context: CallbackContext) -> None:
    if not update.message or not update.message.reply_to_message or not update.message.text:
        return None

    reply_to = update.message.reply_to_message

    origin = reply_to.forward_origin
    if origin is not None and origin.type == MessageOrigin.CHANNEL \
            and origin.chat.id == int(config.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID):
        return await handle_answer_from_channel(update)

    if origin is None and str(reply_to.chat.id) in rooms.keys():
        return await handle_answer_from_room_chat(update)


async def handle_answer_from_channel(update: Update) -> None:
    origin = update.message.reply_to_message.forward_origin
    channel_msg_id = origin.message_id
    if not channel_msg_id:
        log.error(f"forward_origin.message_id is null")
        return None

    question = Question.objects \
        .filter(channel_msg_id=channel_msg_id) \
        .select_related("user", "room") \
        .first()

    if not question:
        log.warning(f"Question with channel_msg_id: {channel_msg_id} is not found")
        return None

    Answer.create_from_update(question, update)

    await notify_user_about_answer(update, question)


async def handle_answer_from_room_chat(update: Update) -> None:
    room_chat_msg_id = update.message.reply_to_message.message_id
    if not room_chat_msg_id:
        log.error(f"reply_to_message.message_id is null")
        return None

    room_chat_id = str(update.message.chat.id)
    room = rooms[room_chat_id]

    question = Question.objects \
        .filter(room=room, room_chat_msg_id=room_chat_msg_id) \
        .select_related("user", "room") \
        .first()

    if not question:
        log.warning(f"Question with room_chat_msg_id: {room_chat_msg_id} is not found")
        return None

    Answer.create_from_update(question, update)

    bot = update.get_bot()

    await notify_user_about_answer(update, question)

    # Forward message to the main channel
    await send_message(
        bot,
        chat_id=config.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_DISCUSSION_ID,
        text=render_html_message(
            template="helpdeskbot_answer_from_room.html",
            reply_chat_id=room_chat_id.replace("-100", ""),
            reply_msg_id=update.message.message_id,
            from_user=update.message.from_user,
            room=room,
            text=update.message.text,
        ),
        reply_to_message_id=question.discussion_msg_id
    )

    # Send confirmation to the room
    question_channel_id = config.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID.replace("-100", "")
    await send_message(
        bot,
        chat_id=int(room_chat_id),
        text=f"➜ <a "
             f"href=\"https://t.me/c/{question_channel_id}/{question.channel_msg_id}\">"
             f"Отвечено</a> 👍"
    )
    return None


async def notify_user_about_answer(update: Update, question: Question) -> None:
    if not question.user:
        log.info(f"User is null for question {question.id}")
        return None

    user_id = question.user.telegram_id
    message = update.message
    from_user = message.from_user
    if int(user_id) == from_user.id:
        log.debug("Reply from the same user, skipping notification")
        return None

    # Send notification to the user
    await send_message(
        update.get_bot(),
        chat_id=int(user_id),
        text=render_html_message(
            template="helpdeskbot_answer_notification.html",
            question=question,
            reply_chat_id=str(message.chat.id).replace("-100", ""),
            reply_msg_id=message.message_id,
            channel_message_link=get_channel_message_link(question.channel_msg_id),
            from_user=message.from_user,
            text=update.message.text,
        )
    )
    return None
