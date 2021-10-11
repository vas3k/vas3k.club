import logging
from datetime import datetime, timedelta

from django.core.management import BaseCommand
from django.template import loader

from notifications.email.sender import send_club_email
from notifications.telegram.common import send_telegram_message, Chat, render_html_message
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send event to a user when their membership expires"

    days_set = [7, 3, 1]

    def handle(self, *args, **options):
        for days in self.days_set:
            # select users to notify
            expired_users = User.objects\
                .filter(
                    is_email_verified=True,
                    membership_expires_at__gte=datetime.utcnow() + timedelta(days=days),
                    moderation_status=User.MODERATION_STATUS_APPROVED
                )\
                .exclude(is_email_unsubscribed=True)
            self.stdout.write(f"days = {days} expired_users =  {expired_users}...")
            for user in expired_users:
                self.stdout.write(f"Sending to {user.email}...")
                try:
                    send_club_email(
                        recipient=user.email,
                        subject=f"Ваша подписка скоро закончится",
                        html=loader.get_template("emails/membership_expire.html").render({"user": user, "days": days}),
                        tags=["membership_expired"]
                    )
                except Exception as ex:
                    log.error(f"Sending to {user.email} failed: {ex}")
                    continue
                self.stdout.write(f"Sending telegram message for {user.telegram_id}...")
                try:
                    send_telegram_message(
                        chat=Chat(id=user.telegram_id),
                        text=render_html_message("membership_expire.html", days=days),
                    )
                except Exception as ex:
                    log.error(f"Sending to {user.telegram_id} failed: {ex}")
                    continue
            self.stdout.write("Done 🥙")
