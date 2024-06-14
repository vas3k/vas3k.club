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

from helpdeskbot.handlers.question import update_discussion_message_id, QuestionHandler
from helpdeskbot.handlers.reply import on_reply_message

from django.conf import settings
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, Filters, MessageHandler

log = logging.getLogger(__name__)

TELEGRAM_ADMIN_BOT_ID = 777000


def on_help_command(update: Update, context: CallbackContext) -> None:
    update.effective_chat.send_message(
        "🤔 <b>Справочная Вастрик.Клуба</b>\n\n"
        "Здесь ты можешь задать свой вопрос и получить ответы.\n\n\n"
        "Список команд:\n\n"
        "/start - Заполнение и отправка вопроса\n"
        "/help - Справка",
        parse_mode=ParseMode.HTML
    )


def on_telegram_admin_bot_message(update: Update, context: CallbackContext) -> None:
    if not update.message:
        return None

    message = update.message
    if message.chat.id == int(settings.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_DISCUSSION_ID) \
        and message.forward_from_chat \
        and message.forward_from_chat.id == int(settings.TELEGRAM_HELP_DESK_BOT_QUESTION_CHANNEL_ID) \
        and message.forward_from_message_id:
        update_discussion_message_id(update)


def main() -> None:
    # Initialize telegram
    updater = Updater(settings.TELEGRAM_HELP_DESK_BOT_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Set handlers
    dispatcher.add_handler(CommandHandler("help", on_help_command))
    dispatcher.add_handler(QuestionHandler("start"))
    dispatcher.add_handler(MessageHandler(Filters.reply & ~Filters.command, on_reply_message))
    dispatcher.add_handler(MessageHandler(Filters.user(TELEGRAM_ADMIN_BOT_ID), on_telegram_admin_bot_message))

    # Start the bot
    if settings.DEBUG:
        updater.start_polling()
        # ^ polling is useful for development since you don't need to expose webhook endpoints
    else:
        updater.start_webhook(
            listen=settings.TELEGRAM_HELP_DESK_BOT_WEBHOOK_HOST,
            port=settings.TELEGRAM_HELP_DESK_BOT_WEBHOOK_PORT,
            url_path=settings.TELEGRAM_HELP_DESK_BOT_TOKEN
        )
        log.info(f"Set webhook: {settings.TELEGRAM_HELP_DESK_BOT_WEBHOOK_URL + settings.TELEGRAM_HELP_DESK_BOT_TOKEN}")
        updater.bot.set_webhook(settings.TELEGRAM_HELP_DESK_BOT_WEBHOOK_URL + settings.TELEGRAM_HELP_DESK_BOT_TOKEN)

    # Wait all threads
    updater.idle()


if __name__ == '__main__':
    main()
