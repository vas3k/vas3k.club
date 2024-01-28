import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode, Bot
from telegram.ext import CallbackContext, ConversationHandler, CommandHandler, MessageHandler, Filters

from askbot.ask_common import is_banned, channel_msg_link, send_html_msg
from askbot.models import Question
from bot.handlers.common import get_club_user
from club import settings
from rooms.models import Room

log = logging.getLogger(__name__)

# States
REQUEST_FOR_INPUT, INPUT_RESPONSE, FINISH_REVIEW = range(3)


# TODO Think about refactoring - splitting for keyboard values and key for storing in the user_data
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
rooms = {r.title: r for r in Room.objects.filter(is_visible=True, chat_id__isnull=False).all()}

def get_rooms_markup() -> list:
    room_names = list(rooms.keys())
    room_names.append(DO_NOT_SEND_ROOM)

    num_columns = 2

    return [room_names[i:i + num_columns] for i in range(0, len(room_names), num_columns)]


room_choose_markup = ReplyKeyboardMarkup(get_rooms_markup())

# TODO refactor
finish_review_keyboard = [
    ["Опубликовать", "Отредактировать"],
    ["Отменить"]
]
finish_review_markup = ReplyKeyboardMarkup(finish_review_keyboard)


def start(update: Update, context: CallbackContext) -> int:
    user = get_club_user(update)
    if not user:
        return ConversationHandler.END

    if is_banned(user):
        update.message.reply_text("🙈 Ты в бане, поэтому не можешь задавать вопросы")
        return ConversationHandler.END

    yesterday = datetime.utcnow() - timedelta(hours=24)
    question_number = Question.objects.filter(user=user) \
        .filter(created_at__gte=yesterday) \
        .count()

    if question_number >= 3:
        update.message.reply_text("Ты очень любознателен(ьна)! Но на сегодня хватит вопросов 😫")
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

    return REQUEST_FOR_INPUT


def question_to_str(user_data: Dict[str, str]) -> str:
    title = f"Заголовок:\n{user_data.get(QKeyboard.TITLE.value, '')}\n\n" if user_data.get(
        QKeyboard.TITLE.value) else ""
    body = f"Текст вопроса:\n{user_data.get(QKeyboard.BODY.value, '')}\n\n\n" if user_data.get(
        QKeyboard.BODY.value) else ""
    tags = f"Теги: {user_data.get(QKeyboard.TAGS.value, '')}\n\n" if user_data.get(QKeyboard.TAGS.value) else ""
    room = f"Выбранная комната: {user_data.get(QKeyboard.ROOM.value, '')}" if user_data.get(
        QKeyboard.ROOM.value) else ""
    return title + body + tags + room


def request_text_value(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    context.user_data[CUR_FIELD_KEY] = text
    update.message.reply_text(f"Пожалуйста введи текст для поля: {text}",
                              reply_markup=ReplyKeyboardRemove())

    return INPUT_RESPONSE


def input_response(update: Update, context: CallbackContext) -> int:
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

    return REQUEST_FOR_INPUT


def request_room_choose(update: Update, context: CallbackContext) -> int:
    context.user_data[CUR_FIELD_KEY] = QKeyboard.ROOM.value
    update.message.reply_text(
        "Выберите комнату в которую отправить ваш вопрос",
        reply_markup=room_choose_markup,
    )
    return INPUT_RESPONSE


def review_question(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data

    title = user_data.get(QKeyboard.TITLE.value, None)
    body = user_data.get(QKeyboard.BODY.value, None)
    if not title or not body:
        update.message.reply_text("Пожалуйста, заполни как минимум заголовок и текст вопроса")
        return edit_question(update, context)

    update.message.reply_text(
        "Заполнение вопроса завершено, давай проверим, что все верно:\n\n"
        f"{question_to_str(user_data)}",
        reply_markup=finish_review_markup,
    )
    return FINISH_REVIEW


def get_room_by_title(title: str) -> Room:
    if not title or title == DO_NOT_SEND_ROOM:
        return None
    else:
        return rooms[title]


# todo refactor - replace Json with an object
def convert_to_user_msg(update: Update, json: Dict[str, str]) -> str:
    user_id = update.effective_user.id
    user_name = update.effective_user["first_name"]
    user_link = f"<a href=\"tg://user?id={user_id}\">{user_name}</a>"
    title = json.get("title")
    body = json.get("body")
    tags = json.get("tags", "")

    # todo fix text
    return (
        f"Вопрос от {user_link}\n\n"
        f"{title}\n\n"
        f"{body}\n\n"
        f"{tags}"
    )


def publish_question(update: Update, user_data: Dict[str, str]) -> str:
    json_text = {
        "title": user_data[QKeyboard.TITLE.value],
        "body": user_data[QKeyboard.BODY.value]
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

    room_chat_msg_text = convert_to_user_msg(update, json_text)

    room = get_room_by_title(room_title)
    room_chat_msg = None
    if room and room.chat_id:
        room_chat_msg = send_html_msg(room.chat_id, room_chat_msg_text)
    else:
        log.warning(f"Chat id is not found for room: {room_title}")

    channel_msg_text = room_chat_msg_text

    if room_chat_msg:
        question.room = room
        question.room_chat_msg_id = room_chat_msg.message_id

        group_link_id = room.chat_id.replace("-100", "")
        group_msg_link = f"https://t.me/c/{group_link_id}/{room_chat_msg.message_id}"
        channel_msg_text = channel_msg_text + "\n\n" + \
                           f"<a href=\"{group_msg_link}\">Ссылка на вопрос в комнате</a>"

    channel_msg = send_html_msg(
        chat_id=settings.TELEGRAM_ASK_BOT_QUESTION_CHANNEL_ID,
        text = channel_msg_text
    )

    question.channel_msg_id = channel_msg.message_id
    question.save()

    return channel_msg_link(channel_msg.message_id)


def edit_question(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Выбери что нужно отредактировать",
        reply_markup=question_markup,
    )
    return REQUEST_FOR_INPUT


def finish_review(update: Update, context: CallbackContext) -> int:
    user_data = context.user_data
    text = update.message.text

    if text == "Опубликовать":
        link = publish_question(update, user_data)
        update.message.reply_text(
            "🎉 Ура! Твой вопрос опубликован. \n"
            f"🔗 <a href=\"{link}\">Ссылка на твой вопрос, там же ты сможешь найти ответы</a>",
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


def fallback(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Похоже ты начал вводить текст не выбрав что именно заполнять. "
        "Пожалуйста, выбери один из вариантов на клавиатуре",
        reply_markup=question_markup,
    )
    return REQUEST_FOR_INPUT


def error_fallback(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        "Что-то пошло не так. Попробуй пожалуйста начать сначала."
    )
    return ConversationHandler.END


start_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        REQUEST_FOR_INPUT: [
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
        INPUT_RESPONSE: [
            MessageHandler(
                Filters.text & ~Filters.command,
                input_response,
            ),
        ],
        FINISH_REVIEW: [
            MessageHandler(
                Filters.text & ~Filters.command,
                finish_review,
            )
        ]
    },
    fallbacks=[MessageHandler(Filters.all, error_fallback)],
)
