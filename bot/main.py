import logging
import os
import sys
import django

# IMPORTANT: this should go before any django-related imports (models, apps, settings)
# These lines must be kept together till THE END
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "club.settings")
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
django.setup()
# THE END

from django.conf import settings
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters, \
    CallbackQueryHandler

from bot.cache import cached_telegram_users
from bot.config import WELCOME_MESSAGE, BOT_MENTION_RE, ANONYMOUS_MESSAGE
from bot.handlers import moderation, comments, upvotes, auth, whois, fun, top, posts, llm

log = logging.getLogger(__name__)


async def command_help(update: Update, context: CallbackContext) -> None:
    await update.effective_chat.send_message(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.HTML
    )


async def private_message(update: Update, context: CallbackContext) -> None:
    log.info("Private message handler triggered")

    club_users = cached_telegram_users()
    if str(update.effective_user.id) not in set(club_users):
        await update.effective_chat.send_message(
            ANONYMOUS_MESSAGE,
            parse_mode=ParseMode.HTML
        )
    else:
        return await llm.llm_response(update, context)


def build_application() -> Application:
    """Build Application with all handlers registered. Does not start polling/webhook."""
    builder = Application.builder().token(settings.TELEGRAM_TOKEN)
    base_url = getattr(settings, 'TELEGRAM_BASE_URL', None)
    if base_url:
        builder = builder.base_url(base_url)
    application = builder.build()

    application.add_handler(CallbackQueryHandler(moderation.approve_post, pattern=r"^approve_post:.+"))
    application.add_handler(CallbackQueryHandler(moderation.forgive_post, pattern=r"^forgive_post:.+"))
    application.add_handler(CallbackQueryHandler(moderation.reject_post, pattern=r"^reject_post.+"))
    application.add_handler(CallbackQueryHandler(moderation.approve_user_profile, pattern=r"^approve_user:.+"))
    application.add_handler(CallbackQueryHandler(moderation.reject_user_profile, pattern=r"^reject_user.+"))

    application.add_handler(CommandHandler("help", command_help))
    application.add_handler(CommandHandler("horo", fun.command_horo))
    application.add_handler(CommandHandler("random", fun.command_random))
    application.add_handler(CommandHandler("top", top.command_top))
    application.add_handler(CommandHandler("whois", whois.command_whois))
    application.add_handler(CallbackQueryHandler(posts.subscribe, pattern=r"^subscribe:.+"))
    application.add_handler(CallbackQueryHandler(posts.unsubscribe, pattern=r"^unsubscribe:.+"))
    application.add_handler(CallbackQueryHandler(upvotes.upvote_post, pattern=r"^upvote_post:.+"))
    application.add_handler(CallbackQueryHandler(upvotes.upvote_comment, pattern=r"^upvote_comment:.+"))
    application.add_handler(
        MessageHandler(filters.REPLY & filters.Regex(r"^\+[+\d ]*$"), upvotes.upvote)
    )

    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(BOT_MENTION_RE), llm.llm_response)
    )

    application.add_handler(
        MessageHandler(filters.REPLY & ~filters.Chat(int(settings.TELEGRAM_ADMIN_CHAT_ID)), comments.comment)
    )

    application.add_handler(CommandHandler("start", auth.command_auth, filters.ChatType.PRIVATE))
    application.add_handler(CommandHandler("auth", auth.command_auth, filters.ChatType.PRIVATE))
    application.add_handler(MessageHandler(filters.FORWARDED & filters.ChatType.PRIVATE, whois.command_whois))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE, private_message))

    return application


def main() -> None:
    application = build_application()

    if settings.DEBUG:
        application.run_polling()
    else:
        application.run_webhook(
            listen=settings.TELEGRAM_BOT_WEBHOOK_HOST,
            port=settings.TELEGRAM_BOT_WEBHOOK_PORT,
            url_path=settings.TELEGRAM_TOKEN,
            webhook_url=settings.TELEGRAM_BOT_WEBHOOK_URL + settings.TELEGRAM_TOKEN,
        )


if __name__ == '__main__':
    main()
