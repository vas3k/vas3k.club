import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict

from django.utils.html import strip_tags
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, Filters

from helpdeskbot import config
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


class ReviewKeyboard(Enum):
    CREATE = "✅ Опубликовать"
    EDIT = "⏮️ Отредактировать"
    CANCEL = "❌ Отменить"


review_markup = ReplyKeyboardMarkup([
    [ReviewKeyboard.CREATE.value, ReviewKeyboard.EDIT.value],
    [ReviewKeyboard.CANCEL.value]
])


class QuestionKeyboard(Enum):
    TITLE = "👉 Заголовок"
    BODY = "📝 Текст вопроса"
    ROOM = "💬 Комната"
    REVIEW = "✅ Запостить"


question_markup = ReplyKeyboardMarkup([
    [QuestionKeyboard.TITLE.value],
    [QuestionKeyboard.BODY.value],
    [QuestionKeyboard.ROOM.value],
    [QuestionKeyboard.REVIEW.value],
])

# It can be either a keyboard key, or the input text from the user
CUR_FIELD_KEY = "cur_field"
DO_NOT_SEND_ROOM = "✖ Без комнаты"

rooms = {f"{strip_tags(r.icon)} {r.title}": r for r in get_rooms()}


def get_rooms_markup() -> list:
    room_names = list(rooms.keys())
    room_names.append(DO_NOT_SEND_ROOM)

    num_columns = 2
    return [room_names[i:i + num_columns] for i in range(0, len(room_names), num_columns)]


room_choose_markup = ReplyKeyboardMarkup(get_rooms_markup())

hyperlink_format = "<a href=\"{href}\">{text}</a>".format


@dataclass
class QuestionDto:
    title: str
    body: str
    room: str = ""

    @classmethod
    def from_user_data(cls, user_data: Dict[str, str]) -> "QuestionDto":
        return QuestionDto(
            title=user_data.get(QuestionKeyboard.TITLE.value, ""),
            body=user_data.get(QuestionKeyboard.BODY.value, ""),
            room=user_data.get(QuestionKeyboard.ROOM.value, "")
        )

    def to_json(self):
        return {
            "title": self.title,
            "body": self.body,
            "room": self.room,
        }


def start(update: Update, context: CallbackContext) -> State:
    user = get_club_user(update)
    if not user:
        return ConversationHandler.END

    help_desk_user_ban = HelpDeskUser.objects.filter(user=user).first()
    if help_desk_user_ban and help_desk_user_ban.is_banned:
        msg_reply(update, "🙈 Вас забанили от пользования Вастрик Справочной")
        return ConversationHandler.END

    yesterday = datetime.utcnow() - timedelta(hours=24)
    question_number = Question.objects.filter(user=user) \
        .filter(created_at__gte=yesterday) \
        .count()

    if question_number >= config.DAILY_QUESTION_LIMIT:
        msg_reply(update, "🙅‍♂️ Вы достигли своего дневного лимита вопросов. Приходите завтра!")
        return ConversationHandler.END

    context.user_data.clear()

    msg_reply(
        update,
        render_html_message("helpdeskbot_welcome.html", user=user),
        reply_markup=question_markup,
    )

    return State.REQUEST_FOR_INPUT


def input_response(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data
    text = update.message.text
    field = user_data[CUR_FIELD_KEY]
    user_data[field] = text
    del user_data[CUR_FIELD_KEY]

    msg_reply(
        update,
        "Принято 👌 Что дальше?",
        reply_markup=question_markup,
    )

    return State.REQUEST_FOR_INPUT


def request_title_value(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QuestionKeyboard.TITLE.value
    msg_reply(
        update,
        f"Введите заголовок вопроса. Он должен кратко и понятно описывать ваш запрос. "
        f"Максимум {config.QUESTION_TITLE_MAX_LEN} символов.",
        reply_markup=ReplyKeyboardRemove()
    )

    return State.INPUT_RESPONSE


def request_body_value(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QuestionKeyboard.BODY.value
    msg_reply(
        update,
        f"Введите текст вопроса. Опишите побольше деталей и контекста. "
        f"Например, ваш город/страну или уже опробованные варианты решений.",
        reply_markup=ReplyKeyboardRemove()
    )

    return State.INPUT_RESPONSE


def request_room_choose(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QuestionKeyboard.ROOM.value
    msg_reply(
        update,
        "Выберите один из чатов, в который бот перепостит ваш вопрос. "
        "Это не обязательно, но увеличивает возможность того, что вам кто-то ответит.",
        reply_markup=room_choose_markup,
    )
    return State.INPUT_RESPONSE


def review_question(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data

    title = user_data.get(QuestionKeyboard.TITLE.value, None)
    body = user_data.get(QuestionKeyboard.BODY.value, None)
    if not title or not body:
        msg_reply(update, "☝️ Заголовок и текст вопроса обязательны для заполнения")
        return edit_question(update, context)

    if len(title) > config.QUESTION_TITLE_MAX_LEN:
        msg_reply(
            update,
            f"😬 Заголовок не должен быть длиннее {config.QUESTION_TITLE_MAX_LEN} символов (у вас {len(title)})"
        )
        return edit_question(update, context)

    if len(body) > config.QUESTION_BODY_MAX_LEN:
        msg_reply(
            update,
            f"😬 Текст вопроса не может быть длиннее {config.QUESTION_BODY_MAX_LEN} символов (у вас {len(body)})"
        )
        return edit_question(update, context)

    msg_reply(
        update,
        render_html_message(
            "helpdeskbot_review_question.html",
            question=QuestionDto.from_user_data(user_data),
            user=get_club_user(update),
            telegram_user=update.effective_user,
        ),
        reply_markup=review_markup,
    )
    return State.FINISH_REVIEW


def publish_question(update: Update, user_data: Dict[str, str]) -> str:
    user = get_club_user(update)
    if not user:
        return ConversationHandler.END

    title = user_data[QuestionKeyboard.TITLE.value]
    body = user_data[QuestionKeyboard.BODY.value]
    json_text = {
        "title": title,
        "body": body
    }

    room_title = user_data.get(QuestionKeyboard.ROOM.value, None)
    if room_title and room_title != DO_NOT_SEND_ROOM:
        json_text["room"] = room_title

    question = Question(
        user=user,
        json_text=json_text
    )
    question.save()

    room_chat_msg_text = render_html_message(
        "helpdeskbot_question.html",
        question=QuestionDto.from_user_data(user_data),
        user=user,
        telegram_user=update.effective_user,
    )

    room = rooms[room_title] if room_title and room_title != DO_NOT_SEND_ROOM else None
    room_chat_msg = None
    if room and room.chat_id:
        room_chat_msg = send_msg(room.chat_id, room_chat_msg_text)

    channel_msg_text = room_chat_msg_text

    if room_chat_msg:
        question.room = room
        question.room_chat_msg_id = room_chat_msg.message_id

        group_msg_link = chat_msg_link(
            chat_id=room.chat_id.replace("-100", ""),
            message_id=room_chat_msg.message_id
        )
        channel_msg_text = (f"{channel_msg_text}\n\n" +
                            hyperlink_format(href=group_msg_link, text="🔗 Ссылка на вопрос в чате"))

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
        "Окей, что редактируем?",
        reply_markup=question_markup,
    )
    return State.REQUEST_FOR_INPUT


def finish_review(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data
    text = update.message.text

    if text == ReviewKeyboard.CREATE.value:
        link = publish_question(update, user_data)
        msg_reply(
            update,
            f"🎉 Вопрос опубликован: <a href=\"{link}\">ссылка и ответы</a>",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    elif text == ReviewKeyboard.EDIT.value:
        return edit_question(update, context)

    elif text == ReviewKeyboard.CANCEL.value:
        msg_reply(
            update,
            "🫡 Создание вопроса отменено. Можно начать заново",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    else:
        raise Exception("😱 Неожиданная команда: " + text)


def fallback(update: Update, context: CallbackContext) -> State:
    msg_reply(
        update,
        "Вы не выбрали действие. Пожалуйста, кликните на один из пунктов меню 👇",
        reply_markup=question_markup,
    )
    return State.REQUEST_FOR_INPUT


def error_fallback(update: Update, context: CallbackContext) -> int:
    msg_reply(
        update,
        "Что-то пошло не так. Придётся начать всё заново :("
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
                        Filters.regex(f"^{QuestionKeyboard.TITLE.value}$"),
                        request_title_value
                    ),
                    MessageHandler(
                        Filters.regex(f"^{QuestionKeyboard.BODY.value}$"),
                        request_body_value
                    ),
                    MessageHandler(
                        Filters.regex(f"^{QuestionKeyboard.ROOM.value}$"),
                        request_room_choose
                    ),
                    MessageHandler(
                        Filters.regex(f"^{QuestionKeyboard.REVIEW.value}$"),
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
