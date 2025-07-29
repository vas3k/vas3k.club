import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict

from django.utils.html import strip_tags
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, Filters

from bot.handlers.common import get_club_user
from helpdeskbot import config
from helpdeskbot.help_desk_common import get_channel_message_link, send_message, send_reply
from helpdeskbot.models import Question, HelpDeskUser
from helpdeskbot.room import get_rooms
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


start_markup = ReplyKeyboardMarkup(
    [["/start"]], resize_keyboard=True
)

review_markup = ReplyKeyboardMarkup([
    [ReviewKeyboard.CREATE.value, ReviewKeyboard.EDIT.value],
    [ReviewKeyboard.CANCEL.value]
])


class QuestionKeyboard(Enum):
    TITLE = "👉 Заголовок"
    BODY = "📝 Текст вопроса"
    ROOM = "💬 Выбрать комнату"
    CANCEL = "❌ Отменить"
    REVIEW = "✅ Запостить"


question_markup = ReplyKeyboardMarkup([
    [QuestionKeyboard.TITLE.value],
    [QuestionKeyboard.BODY.value],
    [QuestionKeyboard.ROOM.value],
    [QuestionKeyboard.CANCEL.value, QuestionKeyboard.REVIEW.value],
])

# It can be either a keyboard key, or the input text from the user
CUR_FIELD_KEY = "cur_field"
DO_NOT_SEND_ROOM = "❌ Без комнаты"

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
            if user_data.get(QuestionKeyboard.ROOM.value, "") != DO_NOT_SEND_ROOM
            else None
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
        send_reply(update, "🙈 Вас забанили от пользования Вастрик Справочной")
        return ConversationHandler.END

    if not user.is_moderator:
        question_count_24h = Question.objects.filter(user=user) \
            .filter(created_at__gte=datetime.utcnow() - timedelta(hours=24)) \
            .count()

        if question_count_24h >= config.DAILY_QUESTION_LIMIT:
            send_reply(update, "🙅‍♂️ Упс, кажется вы превысили свой лимит вопросов в день. Приходите завтра!")
            return ConversationHandler.END

    context.user_data.clear()

    send_reply(
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

    send_reply(
        update,
        "Принято 👌 Что дальше?",
        reply_markup=question_markup,
    )

    return State.REQUEST_FOR_INPUT


def request_title_value(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QuestionKeyboard.TITLE.value
    send_reply(
        update,
        f"Введите заголовок вашего вопроса. Постарайтесь сделать его кратким и понятным. "
        f"Максимум {config.QUESTION_TITLE_MAX_LEN} символов.",
        reply_markup=ReplyKeyboardRemove()
    )

    return State.INPUT_RESPONSE


def request_body_value(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QuestionKeyboard.BODY.value
    send_reply(
        update,
        f"Введите текст вопроса. Опишите побольше деталей и контекста. "
        f"Например, ваш город/страну и уже опробованные варианты решений.",
        reply_markup=ReplyKeyboardRemove()
    )

    return State.INPUT_RESPONSE


def request_room_choose(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QuestionKeyboard.ROOM.value
    send_reply(
        update,
        "Выберите один из чатов, в который бот перепостит ваш вопрос. "
        "Это не обязательно, но может увеличить вероятность того, что там найдётся кто-то, кто знает ответ.",
        reply_markup=room_choose_markup,
    )
    return State.INPUT_RESPONSE


def cancel_question(update: Update, context: CallbackContext) -> State:
    send_reply(
        update,
        "🫡 Создание вопроса отменено. Можно начать заново — /start",
        reply_markup=start_markup,
    )
    return ConversationHandler.END


def review_question(update: Update, context: CallbackContext) -> State:
    data = QuestionDto.from_user_data(context.user_data)

    if not data.title or not data.body:
        send_reply(update, "☝️ Заголовок и текст вопроса обязательны для заполнения")
        return edit_question(update, context)

    if len(data.title) > config.QUESTION_TITLE_MAX_LEN:
        send_reply(
            update,
            f"😬 Заголовок не должен быть длиннее {config.QUESTION_TITLE_MAX_LEN} символов "
            f"(у вас {len(data.title)})"
        )
        return edit_question(update, context)

    if len(data.body) > config.QUESTION_BODY_MAX_LEN:
        send_reply(
            update,
            f"😬 Текст вопроса не может быть длиннее {config.QUESTION_BODY_MAX_LEN} символов "
            f"(у вас {len(data.body)})"
        )
        return edit_question(update, context)

    send_reply(
        update,
        "<b>Создание вопроса завершено, давайте проверим, что все верно ⬇️</b>\n\n" + render_html_message(
            "helpdeskbot_question_in_channel.html",
            question=data,
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

    data = QuestionDto.from_user_data(user_data)
    room = rooms[data.room] if data.room else None

    question = Question(
        user=user,
        json_text=data.to_json()
    )

    channel_message = send_message(
        chat_id=config.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID,
        text=render_html_message(
            "helpdeskbot_question_in_channel.html",
            question=data,
            room=room,
            user=user,
            telegram_user=update.effective_user,
        )
    )

    question.channel_msg_id = channel_message.message_id
    question.save()

    if room and room.chat_id:
        try:
            room_message = send_message(
                chat_id=room.chat_id,
                text=render_html_message(
                    "helpdeskbot_question_in_room.html",
                    question=data,
                    room=room,
                    user=user,
                    telegram_user=update.effective_user,
                    channel_message_link=get_channel_message_link(channel_message.message_id),
                )
            )

            question.room = room
            question.room_chat_msg_id = room_message.message_id
            question.save()
        except Exception as ex:
            log.warning(f"Failed to send message to room: {data.room}. Pls add bot there.", exc_info=ex)

    return get_channel_message_link(channel_message.message_id)


def edit_question(update: Update, context: CallbackContext) -> State:
    send_reply(
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
        send_reply(
            update,
            f"🎉 Вопрос опубликован: <a href=\"{link}\">ссылка и ответы в канале</a>",
            reply_markup=start_markup,
        )
        return ConversationHandler.END

    elif text == ReviewKeyboard.EDIT.value:
        return edit_question(update, context)

    else:
        send_reply(
            update,
            f"😱 Неожиданная команда. Можем начать заново - /start",
            reply_markup=start_markup
        )


def fallback(update: Update, context: CallbackContext) -> State:
    send_reply(
        update,
        "Вы не выбрали действие. Пожалуйста, кликните на один из пунктов меню 👇",
        reply_markup=question_markup,
    )
    return State.REQUEST_FOR_INPUT


def error_fallback(update: Update, context: CallbackContext) -> int:
    send_reply(
        update,
        "Что-то пошло не так. Придётся начать всё заново — /start"
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
                        Filters.regex(f"^{QuestionKeyboard.CANCEL.value}|{ReviewKeyboard.CANCEL.value}$"),
                        cancel_question
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
