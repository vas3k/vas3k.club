import base64
import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.template.defaultfilters import date

from club.exceptions import NotFound
from notifications.digests import generate_daily_digest
from notifications.email.sender import send_club_email
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send daily digest"

    def add_arguments(self, parser):
        parser.add_argument("--production", type=bool, required=False, default=False)

    def handle(self, *args, **options):
        # select daily subscribers
        subscribed_users = User.objects\
            .filter(
                email_digest_type=User.EMAIL_DIGEST_TYPE_DAILY,
                is_email_verified=True,
                membership_expires_at__gte=datetime.utcnow() - timedelta(days=14),
                moderation_status=User.MODERATION_STATUS_APPROVED,
            )\
            .exclude(is_email_unsubscribed=True)

        for user in subscribed_users:
            if not options.get("production") and user.email not in dict(settings.ADMINS).values():
                self.stdout.write("Test mode. Use --production to send the digest to all users")
                continue

            # render user digest using a special html endpoint
            self.stdout.write(f"Generating digest for user: {user.slug}")

            try:
                digest = generate_daily_digest(user)
            except NotFound:
                self.stdout.write("Empty digest. Skipping")
                continue

            digest = digest\
                .replace("%username%", user.slug)\
                .replace("%user_id%", str(user.id))\
                .replace("%secret_code%", base64.b64encode(user.secret_hash.encode("utf-8")).decode())

            self.stdout.write(f"Sending email to {user.email}...")

            try:
                send_club_email(
                    recipient=user.email,
                    subject=f"Дайджест за {date(datetime.utcnow(), 'd E')}",
                    html=digest,
                    tags=["daily_digest"]
                )
            except Exception as ex:
                self.stdout.write(f"Sending to {user.email} failed: {ex}")
                continue

        self.stdout.write("Done 🥙")
