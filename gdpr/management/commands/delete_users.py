import logging
from datetime import datetime

from django.conf import settings
from django.core.management import BaseCommand

from gdpr.forget import delete_user_data
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cron job to actually delete users"

    def handle(self, *args, **options):
        users = User.objects\
            .filter(deleted_at__lte=datetime.utcnow() - settings.GDPR_DELETE_TIMEDELTA)\
            .exclude(moderation_status=User.MODERATION_STATUS_DELETED)

        for user in users:
            self.stdout.write(f"Deleting user: {user.slug}")
            delete_user_data(user)

        self.stdout.write("Done 🥙")
