import logging

from telegram import Update
from telegram.ext import CallbackContext

from helpdeskbot.help_desk_common import channel_msg_link, send_msg
from helpdeskbot.room import get_rooms
from helpdeskbot.models import Question
from club import settings

log = logging.getLogger(__name__)

rooms = {r.chat_id: r for r in get_rooms()}


def handle_reply_from_channel(update: Update) -> None:
    channel_msg_id = update.message.reply_to_message.forward_from_message_id
    if not channel_msg_id:
        log.error(f"forward_from_message_id is null")
        return None

    question = Question.objects\
        .filter(channel_msg_id=channel_msg_id)\
        .select_related("user", "room")\
        .first()
    if not question:
        log.warning(f"Question with channel_msg_id: {channel_msg_id} is not found")
        return None

    notify_user_about_reply(update, question, False)


def handle_reply_from_room_chat(update: Update) -> None:
    room_chat_msg_id = update.message.reply_to_message.message_id
    if not room_chat_msg_id:
        log.error(f"reply_to_message.message_id is null")
        return None

    room_chat_id = str(update.message.chat.id)
    room = rooms[room_chat_id]

    question = Question.objects\
        .filter(room=room, room_chat_msg_id=room_chat_msg_id) \
        .select_related("user", "room")\
        .first()
    if not question:
        log.warning(f"Question with room_chat_msg_id: {room_chat_msg_id} is not found")
        return None

    notify_user_about_reply(update, question, True)

    # Forward message
    from_user = update.message.from_user
    from_user_link = f"<a href=\"tg://user?id={from_user.id}\">{from_user.first_name}</a>"

    reply_chat_id = room_chat_id.replace("-100", "")
    reply_msg_id = update.message.message_id
    reply_chat_link = f"<a href=\"https://t.me/c/{reply_chat_id}/{reply_msg_id}\">Ответ</a>"

    room_invite_link = f"<a href=\"{room.chat_url}\">{room.title}</a>"

    message_text = f"💬 {reply_chat_link} от {from_user_link} из чата {room_invite_link}:\n\n" \
                   f"{update.message.text}"

    chat_id = settings.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_DISCUSSION_ID
    send_msg(chat_id=chat_id, text=message_text, reply_to_message_id=question.discussion_msg_id)


def notify_user_about_reply(update: Update, question: Question, from_room_chat: bool) -> None:
    if not question.user:
        log.info(f"User is null for question {question.id}")
        return None

    user_id = question.user.telegram_id
    message = update.message
    from_user = message.from_user
    if int(user_id) == from_user.id:
        log.debug("Reply from the same user, skipping notification")
        return None

    reply_chat_id = str(message.chat.id).replace("-100", "")
    reply_msg_id = message.message_id
    reply_link = f"<a href=\"https://t.me/c/{reply_chat_id}/{reply_msg_id}\">ответ</a>"
    question_title = question.json_text["title"]

    from_user_link = f"<a href=\"tg://user?id={from_user.id}\">{from_user.first_name}</a>"
    reply_text = message.text

    question_link = f"<a href=\"{channel_msg_link(question.channel_msg_id)}\">❓ Ссылка на твой вопрос</a>"

    if from_room_chat:
        room = question.room
        room_chat_link = f"<a href=\"{room.chat_url}\">{room.title}</a>"
        message_text = \
            f"💬 Новый {reply_link} на вопрос \"{question_title}\" от {from_user_link} из чата {room_chat_link}:\n\n" \
            f"{reply_text}\n\n" \
            f"{question_link}"
    else:
        message_text = \
            f"💬 Новый {reply_link} на вопрос \"{question_title}\" от {from_user_link} из чата канала:\n\n" \
            f"{reply_text}\n\n" \
            f"{question_link}"

    send_msg(chat_id=int(user_id), text=message_text)


def on_reply_message(update: Update, context: CallbackContext) -> None:
    if not update.message \
        or not update.message.reply_to_message \
        or not update.message.text:
        return None

    reply_to = update.message.reply_to_message

    if reply_to.forward_from_chat:
        if reply_to.forward_from_chat.id == int(settings.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID):
            handle_reply_from_channel(update)
            return None
    else:
        if str(reply_to.chat.id) in rooms.keys():
            handle_reply_from_room_chat(update)
            return None
