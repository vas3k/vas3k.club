import base64
import logging
from datetime import timedelta, datetime

from django.conf import settings
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from notifications.email.sender import send_mass_email
from notifications.telegram.common import send_telegram_message, Chat
from posts.models.post import Post
from users.models.user import User

log = logging.getLogger(__name__)


ACTIVITY_THRESHOLD = timedelta(days=365)
SCAN_INTERVAL = timedelta(days=7)


class Command(BaseCommand):
    help = "Notify people with old intros to update them"

    def add_arguments(self, parser):
        parser.add_argument("--production", nargs=1, type=bool, required=False, default=False)

    def handle(self, *args, **options):
        now = datetime.utcnow()
        scan_dates = [
            now.replace(year=y) for y in range(settings.LAUNCH_DATE.year, now.year)
        ]  # scan every year for the same date

        for scan_date in scan_dates:
            expired_intros = Post.objects.filter(
                type=Post.TYPE_INTRO,
                updated_at__gte=scan_date,
                updated_at__lte=scan_date + SCAN_INTERVAL,
                author__moderation_status=User.MODERATION_STATUS_APPROVED,
                author__last_activity_at__gte=now - ACTIVITY_THRESHOLD,
                author__membership_expires_at__gte=now,
            ).select_related("author")

            self.stdout.write(f"Scanning {scan_date}. Found {len(expired_intros)} outdated intros...")
            self.stdout.write(str([intro.author.slug for intro in expired_intros]))

            # debug mode — send everything to vas3k
            if not options.get("production"):
                expired_intros = Post.objects.filter(slug="vas3k")

            for expired_intro in expired_intros:
                user = expired_intro.author

                if user.is_banned:
                    continue

                # try telegram
                if user.telegram_id:
                    self.stdout.write(f"Sending telegram message to {user.slug}...")

                    message = render_to_string("messages/intro_update.html", {
                        "user": user,
                        "intro": expired_intro,
                        "years": now.year - expired_intro.updated_at.year,
                        "settings": settings,
                    })

                    try:
                        send_telegram_message(
                            chat=Chat(id=user.telegram_id),
                            text=message,
                        )

                        continue
                    except Exception as ex:
                        self.stdout.write(f"Telegram to {user.email} failed: {ex}")

                # try email
                if not user.is_email_unsubscribed:
                    self.stdout.write(f"Sending email to {user.email}...")

                    try:
                        email = render_to_string("emails/intro_update.html", {
                            "user": user,
                            "intro": expired_intro,
                            "years": now.year - expired_intro.updated_at.year
                        })

                        secret_code = base64.b64encode(user.secret_hash.encode("utf-8")).decode()
                        email = email \
                            .replace("%username%", user.slug) \
                            .replace("%user_id%", str(user.id)) \
                            .replace("%secret_code%", secret_code)

                        send_mass_email(
                            recipient=user.email,
                            subject=f"Время обновлять интро 👴",
                            html=email,
                            unsubscribe_link=f"{settings.APP_HOST}/notifications/unsubscribe/{user.id}/{secret_code}/"
                        )
                    except Exception as ex:
                        self.stdout.write(f"Email to {user.email} failed: {ex}")

        self.stdout.write("Done 🥙")
