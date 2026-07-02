import logging

from django.core.management import BaseCommand
from telegram.error import TelegramError

from rooms.models import Room
from notifications.telegram.bot import bot
from users.models.user import User

log = logging.getLogger(__name__)


def sync_room_admins_from_telegram(room):
    chat_admins = bot.get_chat_administrators(room.chat_id)
    admin_slugs = []

    for chat_admin in chat_admins:
        if chat_admin.user.is_bot:
            continue

        user = User.objects.filter(telegram_id=str(chat_admin.user.id)).first()
        if user:
            admin_slugs.append(user.slug)

    return sorted(admin_slugs)


class Command(BaseCommand):
    help = "Count members in every telegram chat and save to database"

    def handle(self, *args, **options):
        for room in Room.objects.filter(chat_id__isnull=False):
            update_fields = []

            try:
                room.chat_member_count = bot.get_chat_member_count(room.chat_id)
                update_fields.append("chat_member_count")
            except TelegramError as ex:
                log.warning(f"Failed to get member count for chat {room.slug}: {ex}")

            try:
                room.admins = sync_room_admins_from_telegram(room)
                update_fields.append("admins")
            except TelegramError as ex:
                log.warning(f"Failed to get admins for chat {room.slug}: {ex}")

            if update_fields:
                room.save(update_fields=update_fields)
                log.info(
                    f"Updated chat {room.slug}: "
                    f"{room.chat_member_count} members, {len(room.admins)} admins"
                )

        self.stdout.write("Done 🥙")
