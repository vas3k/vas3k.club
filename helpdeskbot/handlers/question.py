import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, Filters

from helpdeskbot.help_desk_common import channel_msg_link, send_msg, edit_msg, chat_msg_link, msg_reply
from helpdeskbot.models import Question, HelpDeskUser
from helpdeskbot.room import get_rooms
from bot.handlers.common import get_club_user
from club import settings
from notifications.telegram.common import render_html_message

log = logging.getLogger(__name__)


class State(Enum):
    REQUEST_FOR_INPUT = auto()
    INPUT_RESPONSE = auto()
    FINISH_REVIEW = auto()


class QKeyboard(Enum):
    TITLE = "Заголовок"
    BODY = "Текст вопроса"
    TAGS = "Теги"
    ROOM = "Комната"
    REVIEW = "Завершить"


question_keyboard = [
    [QKeyboard.TITLE.value],
    [QKeyboard.BODY.value],
    [QKeyboard.ROOM.value],
    [QKeyboard.TAGS.value],
    [QKeyboard.REVIEW.value],
]
question_markup = ReplyKeyboardMarkup(question_keyboard)

# It can be either a keyboard key, or the input text from the user
CUR_FIELD_KEY = "cur_field"

DO_NOT_SEND_ROOM = "Не отправлять"
rooms = {r.title: r for r in get_rooms()}


def get_rooms_markup() -> list:
    room_names = list(rooms.keys())
    room_names.append(DO_NOT_SEND_ROOM)

    num_columns = 2
    return [room_names[i:i + num_columns] for i in range(0, len(room_names), num_columns)]


room_choose_markup = ReplyKeyboardMarkup(get_rooms_markup())

hyperlink_format = "<a href=\"{href}\">{text}</a>".format


class QuestionDto:
    def __init__(self, title="", body="", tags="", room=""):
        self.title = title
        self.body = body
        self.tags = tags
        self.room = room

    @classmethod
    def from_user_data(cls, user_data: Dict[str, str]) -> "QuestionDto":
        return QuestionDto(
            title=user_data.get(QKeyboard.TITLE.value, ""),
            body=user_data.get(QKeyboard.BODY.value, ""),
            tags=user_data.get(QKeyboard.TAGS.value, ""),
            room=user_data.get(QKeyboard.ROOM.value, "")
        )


def start(update: Update, context: CallbackContext) -> State:
    user = get_club_user(update)
    if not user:
        return ConversationHandler.END

    help_desk_user_ban = HelpDeskUser.objects.filter(user=user).first()
    if help_desk_user_ban and help_desk_user_ban.is_banned:
        msg_reply(update, render_html_message("helpdeskbot_ban.html"))
        return ConversationHandler.END

    yesterday = datetime.utcnow() - timedelta(hours=24)
    question_number = Question.objects.filter(user=user) \
        .filter(created_at__gte=yesterday) \
        .count()

    question_limit = 3
    if question_number >= question_limit:
        msg_reply(update, render_html_message("helpdeskbot_question_limit.html"))
        return ConversationHandler.END

    context.user_data.clear()

    msg_reply(
        update,
        render_html_message("helpdeskbot_welcome.html"),
        reply_markup=question_markup,
    )

    return State.REQUEST_FOR_INPUT


def request_text_value(update: Update, context: CallbackContext) -> State:
    text = update.message.text
    context.user_data[CUR_FIELD_KEY] = text
    msg_reply(
        update,
        render_html_message("helpdeskbot_request_text_value.html", field_name=text),
        reply_markup=ReplyKeyboardRemove()
    )

    return State.INPUT_RESPONSE


def input_response(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data
    text = update.message.text
    field = user_data[CUR_FIELD_KEY]
    user_data[field] = text
    del user_data[CUR_FIELD_KEY]

    msg_reply(
        update,
        render_html_message("helpdeskbot_question_current_state.html", question=QuestionDto.from_user_data(user_data)),
        reply_markup=question_markup,
    )

    return State.REQUEST_FOR_INPUT


def request_room_choose(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QKeyboard.ROOM.value
    msg_reply(
        update,
        render_html_message("helpdeskbot_request_room_choose.html"),
        reply_markup=room_choose_markup,
    )
    return State.INPUT_RESPONSE


def review_question(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data

    title = user_data.get(QKeyboard.TITLE.value, None)
    body = user_data.get(QKeyboard.BODY.value, None)
    if not title or not body:
        msg_reply(update, render_html_message("helpdeskbot_title_body_empty_error.html"))
        return edit_question(update, context)

    title_len_limit = 150
    body_len_limit = 2500
    if len(title) > title_len_limit:
        msg_reply(update, render_html_message("helpdeskbot_title_max_len_error.html", limit=title_len_limit))
        return edit_question(update, context)

    if len(body) > body_len_limit:
        msg_reply(update, render_html_message("helpdeskbot_body_max_len_error.html", limit=body_len_limit))
        return edit_question(update, context)

    msg_reply(
        update,
        render_html_message("helpdeskbot_review_question.html", question=QuestionDto.from_user_data(user_data)),
        reply_markup=ReplyKeyboardMarkup([
            ["Опубликовать", "Отредактировать"],
            ["Отменить"]
        ]),
    )
    return State.FINISH_REVIEW


def publish_question(update: Update, user_data: Dict[str, str]) -> str:
    title = user_data[QKeyboard.TITLE.value]
    body = user_data[QKeyboard.BODY.value]
    json_text = {
        "title": title,
        "body": body
    }
    tags = user_data.get(QKeyboard.TAGS.value, None)
    if tags:
        json_text["tags"] = tags

    room_title = user_data.get(QKeyboard.ROOM.value, None)
    if room_title and room_title != DO_NOT_SEND_ROOM:
        json_text["room"] = room_title

    question = Question(
        user=get_club_user(update),
        json_text=json_text)
    question.save()

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    user_link = hyperlink_format(href=f"tg://user?id={user_id}", text=user_name)

    room_chat_msg_text = \
        f"Вопрос от {user_link}\n\n" \
        f"<b>{title}</b>\n\n" \
        f"{body}"

    if tags:
        room_chat_msg_text = f"{room_chat_msg_text}\n\n{tags}"

    room = rooms[room_title] if room_title and room_title != DO_NOT_SEND_ROOM else None
    room_chat_msg = None
    if room and room.chat_id:
        room_chat_msg = send_msg(room.chat_id, room_chat_msg_text)

    channel_msg_text = room_chat_msg_text

    if room_chat_msg:
        question.room = room
        question.room_chat_msg_id = room_chat_msg.message_id

        group_msg_link = chat_msg_link(
            room.chat_id.replace("-100", ""),
            room_chat_msg.message_id)
        channel_msg_text = (f"{channel_msg_text}\n\n" +
                            hyperlink_format(href=group_msg_link, text="Ссылка на вопрос в тематическом чате"))

    channel_msg = send_msg(
        chat_id=settings.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID,
        text=channel_msg_text
    )

    question.channel_msg_id = channel_msg.message_id
    question.save()

    msg_link = channel_msg_link(channel_msg.message_id)
    if room_chat_msg:
        room_chat_msg_text = (f"{room_chat_msg_text}\n\n" +
                              hyperlink_format(href=msg_link, text="🔗 Ответы на вопрос в канале"))
        edit_msg(chat_id=room.chat_id, message_id=room_chat_msg.message_id, new_text=room_chat_msg_text)
    return msg_link


def edit_question(update: Update, context: CallbackContext) -> State:
    msg_reply(
        update,
        render_html_message("helpdeskbot_edit_question.html"),
        reply_markup=question_markup,
    )
    return State.REQUEST_FOR_INPUT


def finish_review(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data
    text = update.message.text

    if text == "Опубликовать":
        link = publish_question(update, user_data)
        msg_reply(
            update,
            render_html_message("helpdeskbot_question_is_published.html", link=link),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    elif text == "Отредактировать":
        return edit_question(update, context)
    elif text == "Отменить":
        msg_reply(
            update,
            render_html_message("helpdeskbot_edit_canceled.html"),
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    else:
        raise Exception("Неожиданная команда: " + text)


def fallback(update: Update, context: CallbackContext) -> State:
    msg_reply(
        update,
        render_html_message("helpdeskbot_input_without_command_error.html"),
        reply_markup=question_markup,
    )
    return State.REQUEST_FOR_INPUT


def error_fallback(update: Update, context: CallbackContext) -> int:
    msg_reply(
        update,
        render_html_message("helpdeskbot_error_fallback.html")
    )
    return ConversationHandler.END


class QuestionHandler(ConversationHandler):
    def __init__(self, command):
        # Call the constructor of the parent class using super()
        super().__init__(
            entry_points=[CommandHandler(command, start)],
            states={
                State.REQUEST_FOR_INPUT: [
                    MessageHandler(
                        Filters.regex(f"^({QKeyboard.TITLE.value}|{QKeyboard.BODY.value}|{QKeyboard.TAGS.value})$"),
                        request_text_value
                    ),
                    MessageHandler(
                        Filters.regex(f"^{QKeyboard.ROOM.value}$"),
                        request_room_choose
                    ),
                    MessageHandler(
                        Filters.regex(f"^{QKeyboard.REVIEW.value}$"),
                        review_question
                    ),
                    MessageHandler(
                        Filters.text & ~Filters.command,
                        fallback
                    ),
                    CommandHandler("start", start),
                ],
                State.INPUT_RESPONSE: [
                    MessageHandler(
                        Filters.text & ~Filters.command,
                        input_response,
                    ),
                ],
                State.FINISH_REVIEW: [
                    MessageHandler(
                        Filters.text & ~Filters.command,
                        finish_review,
                    )
                ]
            },
            fallbacks=[MessageHandler(Filters.all, error_fallback)],
        )


def update_discussion_message_id(update: Update) -> None:
    channel_msg_id = update.message.forward_from_message_id
    discussion_msg_id = update.message.message_id

    question = Question.objects.filter(channel_msg_id=channel_msg_id).first()
    question.discussion_msg_id = discussion_msg_id
    question.save()
