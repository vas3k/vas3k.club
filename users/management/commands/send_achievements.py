import logging
from datetime import timedelta, datetime

from django.core.management import BaseCommand

from notifications.signals.achievements import async_create_or_update_achievement
from users.models.achievements import UserAchievement

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send achievement notifications"

    def handle(self, *args, **options):
        user_achievements = UserAchievement.objects.filter(created_at__gte=datetime.utcnow() - timedelta(days=14))

        for user_achievement in user_achievements:
            self.stdout.write(
                f"Sending '{user_achievement.achievement.name}' achievement to '{user_achievement.user.slug}'"
            )
            async_create_or_update_achievement(user_achievement)

        self.stdout.write("Done 🥙")
