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

from django.conf import settings
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, Filters, \
    CallbackQueryHandler

from bot.cache import cached_telegram_users
from bot.config import WELCOME_MESSAGE, BOT_MENTION_RE, ANONYMOUS_MESSAGE
from bot.handlers import moderation, comments, upvotes, auth, whois, fun, top, posts, llm

log = logging.getLogger(__name__)


def command_help(update: Update, context: CallbackContext) -> None:
    update.effective_chat.send_message(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.HTML
    )


def private_message(update: Update, context: CallbackContext) -> None:
    log.info("Private message handler triggered")

    club_users = cached_telegram_users()
    if str(update.effective_user.id) not in set(club_users):
        update.effective_chat.send_message(
            ANONYMOUS_MESSAGE,
            parse_mode=ParseMode.HTML
        )
    else:
        return llm.llm_response(update, context)


def main() -> None:
    # Initialize telegram
    updater = Updater(settings.TELEGRAM_TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Admin callbacks
    dispatcher.add_handler(CallbackQueryHandler(moderation.approve_post, pattern=r"^approve_post:.+"))
    dispatcher.add_handler(CallbackQueryHandler(moderation.forgive_post, pattern=r"^forgive_post:.+"))
    dispatcher.add_handler(CallbackQueryHandler(moderation.reject_post, pattern=r"^reject_post.+"))
    dispatcher.add_handler(CallbackQueryHandler(moderation.approve_user_profile, pattern=r"^approve_user:.+"))
    dispatcher.add_handler(CallbackQueryHandler(moderation.reject_user_profile, pattern=r"^reject_user.+"))

    # Commands and buttons
    dispatcher.add_handler(CommandHandler("help", command_help))
    dispatcher.add_handler(CommandHandler("horo", fun.command_horo))
    dispatcher.add_handler(CommandHandler("random", fun.command_random))
    dispatcher.add_handler(CommandHandler("top", top.command_top))
    dispatcher.add_handler(CommandHandler("whois", whois.command_whois))
    dispatcher.add_handler(CallbackQueryHandler(posts.subscribe, pattern=r"^subscribe:.+"))
    dispatcher.add_handler(CallbackQueryHandler(posts.unsubscribe, pattern=r"^unsubscribe:.+"))
    dispatcher.add_handler(CallbackQueryHandler(upvotes.upvote_post, pattern=r"^upvote_post:.+"))
    dispatcher.add_handler(CallbackQueryHandler(upvotes.upvote_comment, pattern=r"^upvote_comment:.+"))
    dispatcher.add_handler(
        MessageHandler(Filters.reply & Filters.regex(r"^\+[+\d ]*$"), upvotes.upvote)
    )

    # AI
    dispatcher.add_handler(
        MessageHandler(Filters.text & Filters.regex(BOT_MENTION_RE), llm.llm_response)
    )

    # Handle comments to posts and replies
    dispatcher.add_handler(
        MessageHandler(Filters.reply & ~Filters.chat(int(settings.TELEGRAM_ADMIN_CHAT_ID)), comments.comment)
    )

    # Private chat with bot
    dispatcher.add_handler(CommandHandler("start", auth.command_auth, Filters.private))
    dispatcher.add_handler(CommandHandler("auth", auth.command_auth, Filters.private))
    dispatcher.add_handler(MessageHandler(Filters.forwarded & Filters.private, whois.command_whois))
    dispatcher.add_handler(MessageHandler(Filters.private, private_message))

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
