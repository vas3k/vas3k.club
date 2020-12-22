import logging

from django.core.management import BaseCommand

from users.models.achievements import UserAchievement, Achievement
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Add achievement to users (separated by comma)"

    def add_arguments(self, parser):
        parser.add_argument("--achievement", type=str, required=False)
        parser.add_argument("--users", type=str, required=True)

    def handle(self, *args, **options):
        achievement_code = options["achievement"]
        usernames = [u.strip().replace("@", "") for u in options["users"].split(",") if u.strip()]

        achievement = Achievement.objects.filter(code=achievement_code).first()
        if not achievement:
            self.stdout.write(f"Achievement not found: '{achievement_code}'")
            return

        users = User.objects.filter(slug__in=usernames)
        for user in users:
            UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
            )

        self.stdout.write("Done 🥙")
