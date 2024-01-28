import logging
import os
import sys

import django

# IMPORTANT: this should go before any django-related imports (models, apps, settings)
# These lines must be kept together till THE END
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "club.settings")
django.setup()
# THE END

from askbot.handlers import question
from askbot.handlers.reply import reply_handler
from askbot.models import Question

from django.conf import settings
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters, MessageHandler

log = logging.getLogger(__name__)


# todo fill out
def command_help(update: Update, context: CallbackContext) -> None:
    update.effective_chat.send_message(
        "🤔 <b>Справочная Вастрик.Клуба</b>\n\n"
        ""
        "Список команд:\n\n"
        "/start - Задать вопрос\n\n"
        "/help - Справка",
        parse_mode=ParseMode.HTML
    )


TELEGRAM_ADMIN_ID = 777000


# TODO move to a new module
def telegram_admin_update(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return None

    message = update.message
    if message.chat.id == int(settings.TELEGRAM_ASK_BOT_QUESTION_CHANNEL_DISCUSSION_ID) \
        and message.forward_from_chat.id == int(settings.TELEGRAM_ASK_BOT_QUESTION_CHANNEL_ID) \
        and message.forward_from_message_id:
        update_discussion_message_id(update)


def update_discussion_message_id(update: Update) -> None:
    channel_msg_id = update.message.forward_from_message_id
    discussion_msg_id = update.message.message_id

    question = Question.objects.filter(channel_msg_id=channel_msg_id).first()
    question.discussion_msg_id = discussion_msg_id
    question.save()


def main() -> None:
    # Initialize telegram
    updater = Updater(settings.TELEGRAM_ASK_BOT_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Set handlers
    dispatcher.add_handler(CommandHandler("help", command_help))
    dispatcher.add_handler(question.start_handler)
    dispatcher.add_handler(MessageHandler(Filters.reply & ~Filters.command, reply_handler))
    dispatcher.add_handler(MessageHandler(Filters.user(TELEGRAM_ADMIN_ID), telegram_admin_update))

    # Start the bot
    if settings.DEBUG:
        updater.start_polling()
        # ^ polling is useful for development since you don't need to expose webhook endpoints
    else:
        updater.start_webhook(
            listen=settings.TELEGRAM_BOT_WEBHOOK_HOST,
            port=settings.TELEGRAM_BOT_WEBHOOK_PORT,
            url_path=settings.TELEGRAM_TOKEN,
        )
        log.info(f"Set webhook: {settings.TELEGRAM_BOT_WEBHOOK_URL + settings.TELEGRAM_TOKEN}")
        updater.bot.set_webhook(settings.TELEGRAM_BOT_WEBHOOK_URL + settings.TELEGRAM_TOKEN)

    # Wait all threads
    updater.idle()


if __name__ == '__main__':
    main()
