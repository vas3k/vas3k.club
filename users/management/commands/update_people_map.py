import logging

from django.core.management import BaseCommand

from users.models.geo import Geo
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Force update map on /people/ page according to city/country names in profile"

    def handle(self, *args, **options):
        users = User.objects.filter(moderation_status=User.MODERATION_STATUS_APPROVED)

        for user in users:
            print(f"Updating for {user.slug} ({user.country}, {user.city})...")
            Geo.update_for_user(user, fuzzy=True)

        self.stdout.write("Done 🥙")
