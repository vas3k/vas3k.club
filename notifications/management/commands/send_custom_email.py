import base64
import logging

from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q
from django.template import loader

from notifications.email.sender import send_mass_email, send_transactional_email
from notifications.telegram.common import send_telegram_message, Chat
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send custom email to specified users"

    def add_arguments(self, parser):
        parser.add_argument("--users", nargs=1, type=str, required=True)
        parser.add_argument("--email-template", nargs=1, type=str, required=True)
        parser.add_argument("--telegram-template", nargs=1, type=str, required=False)
        parser.add_argument("--title", nargs=1, type=str, required=True)
        parser.add_argument("--promo", nargs=1, type=bool, required=False, default=False)

    def handle(self, *args, **options):
        # get users by slugs or emails from the database
        emails_or_slugs = options.get("users")[0].split(",")
        users = User.objects.filter(Q(slug__in=emails_or_slugs) | Q(email__in=emails_or_slugs)).all()

        not_found_users = set(emails_or_slugs) - {user.email for user in users}
        self.stdout.write(
            f"Found {len(users)} registered users: {[user.slug for user in users]}\n"
            f"And {len(not_found_users)} non-club users: {not_found_users}\n"
            f"Confirm sending them emails? [y/n]"
        )

        if input() != "y":
            self.stdout.write("Aborted")
            return

        # find all necessary templates for email and telegram
        email_template = loader.get_template(options.get("email_template")[0])

        telegram_template = None
        if options.get("telegram_template"):
            telegram_template = loader.get_template(options.get("telegram_template")[0])

        is_promo = options.get("promo")

        # send emails to existing users
        for user in users:
            self.stdout.write(f"Sending email to {user.email}...")

            if is_promo and user.is_email_unsubscribed:
                self.stdout.write(f"User {user.email} is unsubscribed from promo emails. Skipping.")
                continue

            secret_code = base64.b64encode(user.secret_hash.encode("utf-8")).decode()
            sender = send_mass_email if is_promo else send_transactional_email
            sender(
                recipient=user.email,
                subject=options.get("title")[0],
                html=email_template.render({"user": user}),
                unsubscribe_link=f"{settings.APP_HOST}/notifications/unsubscribe/{user.id}/{secret_code}/",
            )

            if telegram_template and user.telegram_id:
                self.stdout.write(f"Sending telegram message to {user.telegram_id}...")
                send_telegram_message(
                    chat=Chat(id=user.telegram_id),
                    text=telegram_template.render({"user": user}),
                )

        # send emails to not found users
        for email in not_found_users:
            self.stdout.write(f"Sending email to {email}...")
            send_transactional_email(
                recipient=email,
                subject=options.get("title")[0],
                html=email_template.render(),
            )

        self.stdout.write("Done 🥙")
