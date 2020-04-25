import logging

import telegram
from django.conf import settings

log = logging.getLogger()

bot = telegram.Bot(token=settings.TELEGRAM_TOKEN) if settings.TELEGRAM_TOKEN else None
# dispatcher = Dispatcher(bot, None, workers=0, use_context=True)
