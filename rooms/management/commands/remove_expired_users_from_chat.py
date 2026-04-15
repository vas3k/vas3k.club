import logging
import time
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantsRecent

from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Remove users with expired or missing membership from a telegram chat"

    def add_arguments(self, parser):
        parser.add_argument(
            "--chat-id",
            dest="chat_id",
            type=str,
            required=True,
            help="Telegram chat id (e.g. -1001234567890)",
        )
        parser.add_argument(
            "--execute",
            dest="execute",
            action="store_true",
            help="Actually remove users from chat (false by default)",
        )

    def handle(self, *args, **options):
        chat_id_raw = options.get("chat_id")
        execute = options.get("execute", False)

        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            self.stderr.write(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH are required (set in env or settings). "
                "Get them from https://my.telegram.org"
            )
            return

        if not settings.TELEGRAM_TOKEN:
            self.stderr.write(
                "settings.TELEGRAM_TOKEN (or TELEGRAM_TOKEN) is required. Set in env or settings."
            )
            return

        try:
            api_id = int(settings.TELEGRAM_API_ID)
        except (TypeError, ValueError):
            self.stderr.write("TELEGRAM_API_ID must be an integer")
            return

        client = TelegramClient(
            StringSession(),
            api_id,
            settings.TELEGRAM_API_HASH,
        )

        removed_count = 0
        total_count = 0
        active_count = 0
        expired_count = 0
        non_member_count = 0

        try:
            client.start(bot_token=settings.TELEGRAM_TOKEN)
        except Exception as ex:
            log.exception("Telethon bot start failed")
            self.stderr.write(f"Failed to start Telegram client: {ex}")
            return

        with client:
            try:
                chat_entity = client.get_entity(int(chat_id_raw))
            except Exception as ex:
                log.warning("Failed to get chat entity %s: %s", chat_id_raw, ex)
                self.stderr.write(f"Failed to get chat {chat_id_raw}: {ex}")
                return

            try:
                participants = client.get_participants(
                    chat_entity, limit=None, filter=ChannelParticipantsRecent
                )
            except Exception as ex:
                log.warning("Failed to get participants for %s: %s", chat_id_raw, ex)
                self.stderr.write(f"Failed to get participants for {chat_id_raw}: {ex}")
                return

            try:
                admins = client.get_participants(
                    chat_entity, filter=ChannelParticipantsAdmins
                )
                admin_ids = {p.id for p in admins}
            except Exception as ex:
                log.warning("Failed to get admins for %s: %s", chat_id_raw, ex)
                admin_ids = set()

            for participant in participants:
                total_count += 1
                telegram_id = str(participant.id)

                user = User.objects.filter(telegram_id=telegram_id).first()

                if not user or not user.is_member:
                    status_emoji = "❌"
                    slug = "-"
                    full_name = "-"
                    reason = "not_registered"
                    non_member_count += 1
                elif not user.is_active_membership:
                    status_emoji = "☠️"
                    slug = user.slug
                    full_name = user.full_name
                    reason = "expired"
                    expired_count += 1
                else:
                    status_emoji = "✅"
                    slug = user.slug
                    full_name = user.full_name
                    reason = None
                    active_count += 1

                # force skip admins/moderators
                is_admin = participant.id in admin_ids
                if user and user.is_moderator:
                    is_admin = True

                self.stdout.write(f"{telegram_id} {status_emoji} {slug} {full_name}")

                if execute and reason in {"not_registered", "expired"} and not is_admin:
                    try:
                        # Kick without permanent ban: restrict briefly so they can rejoin later
                        client.edit_permissions(
                            chat_entity,
                            participant,
                            view_messages=False,
                            until_date=datetime.utcnow() + timedelta(minutes=5),
                        )
                        removed_count += 1
                        time.sleep(1.5)
                        log.info(
                            "Removed telegram user %s (%s) from chat %s for reason: %s",
                            telegram_id,
                            slug,
                            chat_id_raw,
                            reason,
                        )
                    except Exception as ex:
                        log.warning(
                            "Failed to remove telegram user %s from chat %s: %s",
                            telegram_id,
                            chat_id_raw,
                            ex,
                        )

        self.stdout.write("")
        self.stdout.write(
            "Statistics: "
            f"total={total_count} | active={active_count} | expired={expired_count} | non-members={non_member_count}"
        )
        self.stdout.write(
            f"Removed {removed_count} ({'executed' if execute else 'dry run'}) 🥙"
        )
