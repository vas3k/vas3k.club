import logging
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Dict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, Filters

from askbot.ask_common import channel_msg_link, send_msg, chat_msg_link
from askbot.models import Question, UserAskBan
from askbot.room import get_rooms
from bot.handlers.common import get_club_user
from club import settings

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


def start(update: Update, context: CallbackContext) -> State:
    user = get_club_user(update)
    if not user:
        return ConversationHandler.END

    user_ask_ban = UserAskBan.objects.filter(user=user).first()
    if user_ask_ban and user_ask_ban.is_banned:
        update.message.reply_text("🙈 Ты в бане, поэтому не можешь задавать вопросы")
        return ConversationHandler.END

    yesterday = datetime.utcnow() - timedelta(hours=24)
    question_number = Question.objects.filter(user=user) \
        .filter(created_at__gte=yesterday) \
        .count()

    question_limit = 3
    if question_number >= question_limit:
        update.message.reply_text("Ты очень любознателен(ьна)! Но на сегодня хватит вопросов, я устал 😫")
        return ConversationHandler.END

    update.message.reply_text(
        "Здравствуй добрый человек 🤗\n\n\n"
        "Я готов начать записывать твой вопрос, но для начала напомню:\n\n"
        "❗️ Флуд и спам запрещены. Тут действуют все <a href=\"https://vas3k.club/docs/about/\">правила Клуба</a>.\n\n"
        "📰 Заголовок должен сразу давать понять суть, а не заигрывать с аудиторией.\n\n"
        "📝 Формулируй вопрос как можно точнее. "
        "Правильный вопрос - половина ответа. Расскажи, что ты уже пробовал(а), и что не получилось.\n\n"
        "#️⃣ Добавление тегов поможет в поиске аналогичных вопросов и ответов, но они не обязательны\n\n\n"
        "Кнопка \"Комната\" позволяет выбрать комнату (клубный тематический чат) в которую также будет "
        "опубликован твой вопрос",
        parse_mode=ParseMode.HTML,
        reply_markup=question_markup,
        disable_web_page_preview=True,
    )

    return State.REQUEST_FOR_INPUT


def question_to_str(user_data: Dict[str, str]) -> str:
    title = f"Заголовок:\n{user_data.get(QKeyboard.TITLE.value, '')}\n\n" if user_data.get(
        QKeyboard.TITLE.value) else ""
    body = f"Текст вопроса:\n{user_data.get(QKeyboard.BODY.value, '')}\n\n\n" if user_data.get(
        QKeyboard.BODY.value) else ""
    tags = f"Теги: {user_data.get(QKeyboard.TAGS.value, '')}\n\n" if user_data.get(QKeyboard.TAGS.value) else ""
    room = f"Комната: {user_data.get(QKeyboard.ROOM.value, '')}" if user_data.get(
        QKeyboard.ROOM.value) else ""
    return title + body + tags + room


def request_text_value(update: Update, context: CallbackContext) -> State:
    text = update.message.text
    context.user_data[CUR_FIELD_KEY] = text
    update.message.reply_text(f"Пожалуйста введи текст для поля: {text}",
                              reply_markup=ReplyKeyboardRemove())

    return State.INPUT_RESPONSE


def input_response(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data
    text = update.message.text
    field = user_data[CUR_FIELD_KEY]
    user_data[field] = text
    del user_data[CUR_FIELD_KEY]

    update.message.reply_text(
        "Сейчас твой вопрос выглядит так: \n\n"
        f"{question_to_str(user_data)}",
        reply_markup=question_markup,
    )

    return State.REQUEST_FOR_INPUT


def request_room_choose(update: Update, context: CallbackContext) -> State:
    context.user_data[CUR_FIELD_KEY] = QKeyboard.ROOM.value
    update.message.reply_text(
        "Выберите комнату в которую отправить твой вопрос",
        reply_markup=room_choose_markup,
    )
    return State.INPUT_RESPONSE


def review_question(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data

    title = user_data.get(QKeyboard.TITLE.value, None)
    body = user_data.get(QKeyboard.BODY.value, None)
    if not title or not body:
        update.message.reply_text("Пожалуйста, заполни как минимум заголовок и текст вопроса")
        return edit_question(update, context)

    title_len_limit = 150
    body_len_limit = 2500
    if len(title) > title_len_limit:
        update.message.reply_text(
            f"Заголовок вопроса превышает максимальную длину {title_len_limit}. Поправь пожалуйста.")
        return edit_question(update, context)

    if len(body) > body_len_limit:
        update.message.reply_text(f"Текст вопроса превышает максимальную длину {body_len_limit}. Поправь пожалуйста.")
        return edit_question(update, context)

    update.message.reply_text(
        "Заполнение вопроса завершено, давай проверим, что все верно:\n\n"
        f"{question_to_str(user_data)}",
        reply_markup=ReplyKeyboardMarkup([
            ["Опубликовать", "Отредактировать"],
            ["Отменить"]
        ]
        ),
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
        chat_id=settings.TELEGRAM_ASK_BOT_QUESTION_CHANNEL_ID,
        text=channel_msg_text
    )

    question.channel_msg_id = channel_msg.message_id
    question.save()

    return channel_msg_link(channel_msg.message_id)


def edit_question(update: Update, context: CallbackContext) -> State:
    update.message.reply_text(
        "Выбери что нужно отредактировать",
        reply_markup=question_markup,
    )
    return State.REQUEST_FOR_INPUT


def finish_review(update: Update, context: CallbackContext) -> State:
    user_data = context.user_data
    text = update.message.text

    if text == "Опубликовать":
        link = publish_question(update, user_data)
        update.message.reply_text(
            "🎉 Ура! Твой вопрос опубликован. \n" +
            hyperlink_format(href=link, text="Ссылка на твой вопрос, там же ты сможешь найти ответы"),
            reply_markup=ReplyKeyboardRemove(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
        return ConversationHandler.END
    elif text == "Отредактировать":
        return edit_question(update, context)
    elif text == "Отменить":
        update.message.reply_text(
            "Заполнение вопроса отменено. Если хочешь начать сначала введи команду /start",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    else:
        raise Exception("Неожиданная команда: " + text)


def fallback(update: Update, context: CallbackContext) -> State:
    update.message.reply_text(
        "Похоже ты начал вводить текст не выбрав что именно заполнять. "
        "Пожалуйста, выбери один из вариантов на клавиатуре",
        reply_markup=question_markup,
    )
    return State.REQUEST_FOR_INPUT


def error_fallback(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Что-то пошло не так. Попробуй пожалуйста начать сначала."
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
                    )
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
