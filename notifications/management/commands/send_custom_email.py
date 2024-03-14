import base64
import logging

from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q
from django.template import loader
from django_q.tasks import async_task

from notifications.email.sender import send_mass_email, send_transactional_email
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send custom email to specified users"

    def add_arguments(self, parser):
        parser.add_argument("--users", nargs=1, type=str, required=True)
        parser.add_argument("--template", nargs=1, type=str, required=True)
        parser.add_argument("--title", nargs=1, type=str, required=True)
        parser.add_argument("--promo", nargs=1, type=bool, required=False, default=False)

    def handle(self, *args, **options):
        # get users by slugs or emails from the database
        emails_or_slugs = options.get("users").split(",")
        users = User.objects.filter(Q(slug__in=emails_or_slugs) | Q(email__in=emails_or_slugs)).all()

        if len(emails_or_slugs) != len(users):
            self.stdout.write(
                f"Some users are not found. "
                f"Found {len(users)} out of {len(emails_or_slugs)}. "
                f"Do you want to continue? [y/n]"
            )
            if input() != "y":
                return

        # find the template
        is_promo = options.get("promo")
        template = loader.get_template(options.get("template"))

        for user in users:
            self.stdout.write(f"Sending email to {user.email}...")

            if is_promo and user.is_email_unsubscribed:
                self.stdout.write(f"User {user.email} is unsubscribed from promo emails. Skipping.")
                continue

            secret_code = base64.b64encode(user.secret_hash.encode("utf-8")).decode()

            async_task(
                send_mass_email if is_promo else send_transactional_email,
                recipient=user.email,
                subject=options.get("title"),
                html=template.render({"user": user}),
                unsubscribe_link=f"{settings.APP_HOST}/notifications/unsubscribe/{user.id}/{secret_code}/",
            )

        self.stdout.write("Done 🥙")
