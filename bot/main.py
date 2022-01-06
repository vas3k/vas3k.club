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
from bot.handlers import moderation, comments, upvotes, auth, whois, fun, top

log = logging.getLogger(__name__)


def command_help(update: Update, context: CallbackContext) -> None:
    update.effective_chat.send_message(
        "🌍️ <b>Я — твой личный бот для 4aff.Клуба</b>\n\n"
        "Через меня можно отвечать на комменты и посты — просто напиши "
        "ответ реплаем на сообщение и я перепостю его в Клуб. "
        "Так можно общаться в комментах даже не открывая сайт.\n\n"
        "Чтобы плюсануть — реплайни +.\n\n"
        "Еще я знаю всякие команды:\n\n"
        "/top - Топ событий в Клубе\n\n"
        "/random - Почитать случайный пост (неплохо убивает время)\n\n"
        "/whois - Узнать профиль по телеграму\n\n"
        "/horo - Клубный гороскоп\n\n"
        "/auth - Привязать бота к аккаунту в Клубе\n\n"
        "/help - Справка",
        parse_mode=ParseMode.HTML
    )


def private_message(update: Update, context: CallbackContext) -> None:
    club_users = cached_telegram_users()
    if str(update.effective_user.id) not in set(club_users):
        update.effective_chat.send_message(
            "Привет! Мы пока не знакомы. Привяжи меня к аккаунту командой /auth с "
            "<a href=\"https://4aff.club/user/me/edit/bot/\">кодом из профиля</a> через пробел",
            parse_mode=ParseMode.HTML
        )
    else:
        update.effective_chat.send_message(
            "Йо! Полный список моих команд покажет /help,"
            "а еще мне можно отвечать на посты и уведомления, всё это будет поститься прямо в Клуб!",
            parse_mode=ParseMode.HTML
        )


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
    dispatcher.add_handler(CommandHandler("promote", moderation.command_promote_user))

    # Public + private chats
    dispatcher.add_handler(CommandHandler("help", command_help))
    dispatcher.add_handler(CommandHandler("horo", fun.command_horo))
    dispatcher.add_handler(CommandHandler("random", fun.command_random))
    dispatcher.add_handler(CommandHandler("top", top.command_top))
    dispatcher.add_handler(CommandHandler("whois", whois.command_whois))
    dispatcher.add_handler(
        MessageHandler(Filters.reply & Filters.regex(r"^\+[+\d ]*$"), upvotes.upvote)
    )
    dispatcher.add_handler(
        MessageHandler(Filters.reply & ~Filters.chat(int(settings.TELEGRAM_ADMIN_CHAT_ID)), comments.comment)
    )

    # Only private chats
    dispatcher.add_handler(CommandHandler("start", auth.command_auth, Filters.private))
    dispatcher.add_handler(CommandHandler("auth", auth.command_auth, Filters.private))
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
