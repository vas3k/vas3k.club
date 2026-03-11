import logging

from django.core.management import BaseCommand
from telegram.error import TelegramError

from rooms.models import Room
from notifications.telegram.bot import bot

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Count members in every telegram chat and save to database"

    def handle(self, *args, **options):
        for room in Room.objects.filter(chat_id__isnull=False):
            try:
                member_count = bot.get_chat_member_count(room.chat_id)

                # Store the count in the database
                room.chat_member_count = member_count
                room.save()

                log.info(f"Updated member count for chat {room.slug}: {member_count} members")

            except TelegramError as ex:
                log.warning(f"Failed to get member count for chat {room.slug}: {ex}")

        self.stdout.write("Done 🥙")
