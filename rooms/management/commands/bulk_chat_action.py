import logging

from django.core.management import BaseCommand
from django.db.models import Q

from rooms.helpers import ban_user_in_all_chats, unban_user_in_all_chats
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Perform bulk action on user in all telegram rooms"

    def add_arguments(self, parser):
        parser.add_argument("--users", nargs=1, type=str, required=True)
        parser.add_argument("--action", nargs=1, type=str, required=True)

    def handle(self, *args, **options):
        action = options.get("action")[0]
        emails_or_slugs = options.get("users")[0].split(",")

        for email_or_slugs in emails_or_slugs:
            user = User.objects.filter(Q(email=email_or_slugs) | Q(slug=email_or_slugs)).first()
            if not user:
                self.stderr.write(f"No such user: {email_or_slugs}")

            if action == "ban":
                ban_user_in_all_chats(user)
            elif action == "unban":
                unban_user_in_all_chats(user)
            else:
                self.stderr.write(f"Wrong action: {action}")

        self.stdout.write("Done 🥙")
