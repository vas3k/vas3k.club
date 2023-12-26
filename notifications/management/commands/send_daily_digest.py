import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand

from club.exceptions import NotFound
from notifications.digests import generate_daily_digest
from notifications.telegram.common import send_telegram_message, Chat
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send daily digest"

    def add_arguments(self, parser):
        parser.add_argument("--production", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        # select daily subscribers
        if not options.get("production"):
            subscribed_users = User.objects.filter(
                email__in=dict(settings.ADMINS).values(),
                telegram_id__isnull=False
            )
        else:
            subscribed_users = User.objects\
                .filter(
                    email_digest_type=User.EMAIL_DIGEST_TYPE_DAILY,
                    membership_expires_at__gte=datetime.utcnow(),
                    moderation_status=User.MODERATION_STATUS_APPROVED,
                    deleted_at__isnull=True,
                )

        for user in subscribed_users:
            if not user.telegram_id:
                self.stdout.write("User does not have telegram ID in profile")
                continue

            # render user digest using a special html endpoint
            self.stdout.write(f"Generating digest for user: {user.slug}")

            try:
                digest = generate_daily_digest(user)
            except NotFound:
                self.stdout.write("Empty digest. Skipping")
                continue

            self.stdout.write(f"Sending message to {user.slug}...")

            try:
                send_telegram_message(
                    chat=Chat(id=user.telegram_id),
                    text=digest,
                )
            except Exception as ex:
                self.stdout.write(f"Sending to {user.email} failed: {ex}")
                continue

        self.stdout.write("Done 🥙")
