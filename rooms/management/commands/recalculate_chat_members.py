import logging
import time
from datetime import datetime

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from telethon.errors import FloodWaitError, RPCError
from telethon.sessions import StringSession
from telethon.sync import TelegramClient
from telethon.tl.types import ChannelParticipantBanned, ChannelParticipantLeft, ChannelParticipantsRecent

from rooms.models import Room, RoomSubscription
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconcile Telegram room membership without changing notification preferences"

    def add_arguments(self, parser):
        parser.add_argument("--chat-id", help="Recalculate only this Telegram chat")
        parser.add_argument("--retries", type=int, default=2, help="Retry failed rooms this many times (default: 2)")
        parser.add_argument(
            "--retry-delay", type=int, default=60,
            help="Initial delay between retry passes in seconds, doubled each pass (default: 60)",
        )

    def handle(self, *args, **options):
        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH or not settings.TELEGRAM_TOKEN:
            raise CommandError("TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_TOKEN are required")

        if options["retries"] < 0 or options["retry_delay"] < 0:
            raise CommandError("--retries and --retry-delay must be non-negative")

        rooms = Room.objects.filter(chat_id__isnull=False).exclude(chat_id="")

        if options["chat_id"]:
            rooms = rooms.filter(chat_id=options["chat_id"])

        client = TelegramClient(StringSession(), int(settings.TELEGRAM_API_ID), settings.TELEGRAM_API_HASH)
        failed_rooms = []

        try:
            client.start(bot_token=settings.TELEGRAM_TOKEN)

            pending_rooms = list(rooms)

            for attempt in range(options["retries"] + 1):
                retry_rooms = []

                for room in pending_rooms:
                    started_at = datetime.utcnow()

                    try:
                        participants = client.get_participants(
                            int(room.chat_id), limit=None, filter=ChannelParticipantsRecent,
                        )
                    except (RPCError, ValueError, OSError) as ex:
                        log.warning("Failed to fetch members for %s: %s", room.slug, ex)

                        if isinstance(ex, FloodWaitError):
                            wait_seconds = ex.seconds + 1
                            self.stdout.write(f"Telegram rate limit: waiting {wait_seconds}s before continuing")
                            time.sleep(wait_seconds)

                        retry_rooms.append(room)
                        continue

                    if len(participants) < participants.total:
                        log.warning("Incomplete member list for %s; skipping reconciliation", room.slug)
                        failed_rooms.append(room.slug)
                        continue

                    telegram_ids = []

                    for participant in participants:
                        if participant.bot:
                            continue

                        membership = participant.participant

                        if isinstance(membership, ChannelParticipantLeft):
                            continue

                        if isinstance(membership, ChannelParticipantBanned):
                            if membership.left or membership.banned_rights.view_messages:
                                continue

                        telegram_ids.append(str(participant.id))

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

                if not retry_rooms or attempt == options["retries"]:
                    failed_rooms.extend(room.slug for room in retry_rooms)
                    break

                delay = options["retry_delay"] * (2 ** attempt)
                self.stdout.write(
                    f"Retrying {len(retry_rooms)} failed rooms in {delay}s "
                    f"(retry {attempt + 1}/{options['retries']})"
                )
                time.sleep(delay)
                pending_rooms = retry_rooms
        finally:
            client.disconnect()

        if failed_rooms:
            raise CommandError(f"Failed to reconcile rooms: {', '.join(failed_rooms)}")

        self.stdout.write("Done 🥙")
