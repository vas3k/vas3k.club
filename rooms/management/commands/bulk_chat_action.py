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

        identifiers = set(emails_or_slugs)
        users_qs = User.objects.filter(Q(email__in=identifiers) | Q(slug__in=identifiers))
        users_by_email = {}
        users_by_slug = {}
        for user in users_qs:
            users_by_email[user.email] = user
            users_by_slug[user.slug] = user

        for identifier in emails_or_slugs:
            user = users_by_email.get(identifier) or users_by_slug.get(identifier)
            if not user:
                self.stderr.write(f"No such user: {identifier}")
                continue

            if action == "ban":
                ban_user_in_all_chats(user, is_permanent=True)
            elif action == "unban":
                unban_user_in_all_chats(user)
            else:
                self.stderr.write(f"Wrong action: {action}")

        self.stdout.write("Done 🥙")
