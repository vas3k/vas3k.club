import logging

import telegram
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from telegram import Update

from bot.common import send_telegram_message, Chat
from bot.handlers.common import get_bot_user
from posts.forms.compose import PostTextForm, POST_TYPE_MAP
from posts.models import Post
from users.models.user import User

BOT_USER_POST_KEY = "bot:user:{}:post"
BOT_USER_POST_TTL = 60 * 60 * 48  # 48 hour

log = logging.getLogger(__name__)


def process_auth(update: Update):
    user = None
    if update.message and update.message.text:
        user = User.objects.filter(secret_hash=str(update.message.text).strip()).first()

    if not user:
        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text="Привет. Мы пока не знакомы. Привяжи меня на сайте или пришли мне секретный код 👇"
        )
        return

    user.telegram_id = update.effective_user.id
    user.telegram_data = {
        "id": update.effective_user.id,
        "username": update.effective_user.username,
        "first_name": update.effective_user.first_name,
        "last_name": update.effective_user.last_name,
        "language_code": update.effective_user.language_code,
    }
    user.save()

    send_telegram_message(
        chat=Chat(id=update.effective_chat.id),
        text=f"Отлично! Приятно познакомиться, {user.slug}"
    )
    cache.delete("bot:telegram_user_ids")


def process_personal_chat_updates(update: Update):
    user = get_bot_user(update)
    if not user:
        return

    # check for unfinished posts
    unfinished_post = cached_post_get(update.effective_user.id)

    # found an unfinished post
    if unfinished_post:
        reply = continue_posting(update, unfinished_post, user)
        if reply:
            send_telegram_message(
                chat=Chat(id=update.effective_chat.id),
                text=reply
            )
        return

    # parse forwarded posts and links
    if update.message:
        reply = parse_forwarded_messages(update)
        if reply:
            send_telegram_message(
                chat=Chat(id=update.effective_chat.id),
                text=reply
            )
        return

    send_telegram_message(
        chat=Chat(id=update.effective_chat.id),
        text="Чот непонятна 🤔"
    )


def parse_forwarded_messages(update: Update):
    started_post = {
        "title": None,
        "type": Post.TYPE_POST,
        "text": update.message.text or update.message.caption,
        "url": None,
        "is_visible": True,
        "is_public": True,
    }
    for entity, text in update.message.parse_entities().items():
        if entity.type == "url":
            started_post["url"] = text
        elif entity.type == "bold":
            started_post["title"] = text

    # save it to user cache
    cached_post_set(update.effective_user.id, started_post)

    if started_post["url"]:
        # looks like a link
        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text=f"Выглядит как ссылка. Хотите поделиться ей в Клубе? Как будем постить?",
            reply_markup=telegram.InlineKeyboardMarkup([
                [
                    telegram.InlineKeyboardButton("🔗 Ссылкой", callback_data=f"link"),
                    telegram.InlineKeyboardButton("📝 Как пост", callback_data=f"post"),
                ],
                [
                    telegram.InlineKeyboardButton("❌ Отмена", callback_data=f"nope"),
                ]
            ])
        )
    else:
        # looks like a text post
        if len(started_post["text"] or "") < 120:
            return "Напиши или форвардни мне нормальный пост или ссылку!"

        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text=f"Хотите поделиться этим в Клубе? Как будем постить?",
            reply_markup=telegram.InlineKeyboardMarkup([
                [
                    telegram.InlineKeyboardButton("📝 Как пост", callback_data=f"post"),
                    telegram.InlineKeyboardButton("❔ Вопросом", callback_data=f"question"),
                ],
                [
                    telegram.InlineKeyboardButton("❌ Отмена", callback_data=f"nope"),
                ]
            ])
        )


def continue_posting(update: Update, started_post: dict, user: User):
    if update.callback_query:
        if update.callback_query.data == "nope":
            # cancel posting
            cached_post_delete(update.effective_user.id)
            return "Ок, забыли 👌"

        elif update.callback_query.data in {"post", "link", "question"}:
            # ask for title
            started_post["type"] = update.callback_query.data
            cached_post_set(update.effective_user.id, started_post)
            return f"Отлично. Теперь надо придумать заголовок, чтобы всем было понятно о чем это. " \
                   f"Подумайте и пришлите его следующим сообщением 👇"

        elif update.callback_query.data == "go":
            # go-go-go, post the post
            FormClass = POST_TYPE_MAP.get(started_post["type"]) or PostTextForm

            form = FormClass(started_post)
            if not form.is_valid():
                return f"🤦‍♂️ Что-то пошло не так. Пришлите нам багрепорт. " \
                       f"Вот ошибка:\n```{str(form.errors)}```"

            if Post.check_duplicate(user=user, title=form.cleaned_data["title"]):
                return "🤔 Выглядит как дубликат вашего прошлого поста. " \
                       "Проверьте всё ли в порядке и пришлите ниже другой заголовок 👇"

            is_ok = Post.check_rate_limits(user)
            if not is_ok:
                return "🙅‍♂️ Извините, вы сегодня запостили слишком много постов. Попробуйте попозже"

            post = form.save(commit=False)
            post.author = user
            post.type = started_post["type"]
            post.meta = {"telegram": update.to_json()}
            post.save()

            post_url = settings.APP_HOST + reverse("show_post", kwargs={
                "post_type": post.type,
                "post_slug": post.slug
            })
            cached_post_delete(update.effective_user.id)
            return f"Запостили 🚀🚀🚀\n\n{post_url}"

    if update.message:
        started_post["title"] = str(update.message.text or update.message.caption or "").strip()[:128]
        if len(started_post["title"]) < 7:
            send_telegram_message(
                chat=Chat(id=update.effective_chat.id),
                text=f"Какой-то короткий заголовок. Пришлите другой, подлинее",
                reply_markup=telegram.InlineKeyboardMarkup([
                    [
                        telegram.InlineKeyboardButton("❌ Отменить всё", callback_data=f"nope"),
                    ]
                ])
            )
            return

        cached_post_set(update.effective_user.id, started_post)
        emoji = Post.TYPE_TO_EMOJI.get(started_post["type"]) or "🔥"
        send_telegram_message(
            chat=Chat(id=update.effective_chat.id),
            text=f"Заголовок принят. Теперь пост выглядит как-то так:\n\n"
                 f"{emoji} <b>{started_post['title']}</b>\n\n"
                 f"{started_post['text'] or ''}\n\n"
                 f"{started_post['url'] or ''}\n\n"
                 f"<b>Будем постить?</b> (после публикации его можно будет подредактировать на сайте)",
            reply_markup=telegram.InlineKeyboardMarkup([
                [
                    telegram.InlineKeyboardButton("✅ Поехали", callback_data=f"go"),
                    telegram.InlineKeyboardButton("❌ Отмена", callback_data=f"nope"),
                ],
            ])
        )


def cached_post_get(telegram_user_id):
    return cache.get(BOT_USER_POST_KEY.format(telegram_user_id))


def cached_post_set(telegram_user_id, data):
    return cache.set(
        BOT_USER_POST_KEY.format(telegram_user_id),
        data,
        BOT_USER_POST_TTL
    )


def cached_post_delete(telegram_user_id):
    return cache.delete(BOT_USER_POST_KEY.format(telegram_user_id))
