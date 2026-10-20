import logging
import time
from datetime import timedelta

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from telethon.errors import FloodWaitError, RPCError
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantsRecent

from users.models.user import User

log = logging.getLogger(__name__)


def telegram_request_with_retries(request, *args, retries, retry_delay, **kwargs):
    for attempt in range(retries + 1):
        try:
            return request(*args, **kwargs)
        except (RPCError, ValueError, OSError) as ex:
            if attempt == retries:
                raise

            delay = ex.seconds + 1 if isinstance(ex, FloodWaitError) else retry_delay * (2 ** attempt)
            log.warning("Telegram request failed: %s; retrying in %ss (%s/%s)", ex, delay, attempt + 1, retries)
            time.sleep(delay)


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

        parser.add_argument("--retries", type=int, default=2, help="Retries per failed Telegram request (default: 2)")
        parser.add_argument(
            "--retry-delay", type=int, default=60,
            help="Initial retry delay in seconds, doubled each retry (default: 60)",
        )

    def handle(self, *args, **options):
        chat_id_raw = options.get("chat_id")
        execute = options.get("execute", False)
        retry_options = {"retries": options["retries"], "retry_delay": options["retry_delay"]}

        if min(retry_options.values()) < 0:
            raise CommandError("--retries and --retry-delay must be non-negative")

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
            telegram_request_with_retries(client.start, bot_token=settings.TELEGRAM_TOKEN, **retry_options)
        except Exception as ex:
            log.exception("Telethon bot start failed")
            client.disconnect()
            raise CommandError(f"Failed to start Telegram client: {ex}") from ex

        with client:
            try:
                chat_entity = telegram_request_with_retries(client.get_entity, int(chat_id_raw), **retry_options)
            except Exception as ex:
                log.warning("Failed to get chat entity %s: %s", chat_id_raw, ex)
                raise CommandError(f"Failed to get chat {chat_id_raw}: {ex}") from ex

            try:
                participants = telegram_request_with_retries(
                    client.get_participants, chat_entity, limit=None, filter=ChannelParticipantsRecent, **retry_options,
                )
            except Exception as ex:
                log.warning("Failed to get participants for %s: %s", chat_id_raw, ex)
                raise CommandError(f"Failed to get participants for {chat_id_raw}: {ex}") from ex

            try:
                admins = telegram_request_with_retries(
                    client.get_participants, chat_entity, limit=None, filter=ChannelParticipantsAdmins, **retry_options,
                )
                admin_ids = {p.id for p in admins}
            except Exception as ex:
                log.warning("Failed to get admins for %s: %s", chat_id_raw, ex)
                raise CommandError(f"Failed to get admins for {chat_id_raw}; no users removed: {ex}") from ex

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
                        # A relative expiry stays in the future after retries; a past expiry would ban forever.
                        telegram_request_with_retries(
                            client.edit_permissions, chat_entity,
                            participant,
                            view_messages=False,
                            until_date=timedelta(minutes=5),
                            **retry_options,
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
