import logging

from django.conf import settings
from django.core.management import BaseCommand
from django.urls import reverse

from notifications.telegram.bot import bot

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set telegram webhook"

    def handle(self, *args, **options):
        # setWebhook for the bot
        if settings.TELEGRAM_TOKEN:
            webhook_uri = reverse("webhook_telegram", kwargs={"token": settings.TELEGRAM_TOKEN})
            bot.set_webhook("https://vas3k.club" + webhook_uri)

        self.stdout.write("Done 🥙")
