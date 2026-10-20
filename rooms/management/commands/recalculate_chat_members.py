import logging
from datetime import datetime

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from telethon.errors import RPCError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

from rooms.models import Room, RoomSubscription
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconcile Telegram room membership without changing notification preferences"

    def add_arguments(self, parser):
        parser.add_argument("--chat-id", help="Recalculate only this Telegram chat")

    def handle(self, *args, **options):
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH or not settings.TELEGRAM_TOKEN:
            raise CommandError("TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_TOKEN are required")

        rooms = Room.objects.filter(chat_id__isnull=False).exclude(chat_id="")

        if options["chat_id"]:
            rooms = rooms.filter(chat_id=options["chat_id"])

        client = TelegramClient(StringSession(), int(settings.TELEGRAM_API_ID), settings.TELEGRAM_API_HASH)
        failed_rooms = []

        try:
            client.start(bot_token=settings.TELEGRAM_TOKEN)

            for room in rooms:
                started_at = datetime.utcnow()

                try:
                    participants = client.get_participants(int(room.chat_id), limit=None)
                except (RPCError, ValueError) as ex:
                    log.warning("Failed to fetch members for %s: %s", room.slug, ex)
                    failed_rooms.append(room.slug)
                    continue

                if len(participants) < participants.total:
                    log.warning("Incomplete member list for %s; skipping reconciliation", room.slug)
                    failed_rooms.append(room.slug)
                    continue

                telegram_ids = [str(participant.id) for participant in participants if not participant.bot]
                users = list(User.objects.filter(telegram_id__in=telegram_ids))
                user_ids = [user.id for user in users]

                with transaction.atomic():
                    RoomSubscription.objects.bulk_create([
                        RoomSubscription(
                            user=user, room=room, is_chat_member=True, is_notified=False,
                            chat_membership_updated_at=started_at,
                        )
                        for user in users
                    ], ignore_conflicts=True, batch_size=1000)

                    # Webhook events received during the fetch are newer than this snapshot.
                    subscriptions = RoomSubscription.objects.filter(room=room).filter(
                        Q(chat_membership_updated_at__isnull=True) | Q(chat_membership_updated_at__lte=started_at),
                    )
                    subscriptions.filter(user_id__in=user_ids).update(
                        is_chat_member=True, chat_membership_updated_at=started_at,
                    )
                    subscriptions.exclude(user_id__in=user_ids).update(
                        is_chat_member=False, chat_membership_updated_at=started_at,
                    )

                self.stdout.write(f"{room.slug}: {len(users)} club members")
        finally:
            client.disconnect()

        if failed_rooms:
            raise CommandError(f"Failed to reconcile rooms: {', '.join(failed_rooms)}")

        self.stdout.write("Done 🥙")
