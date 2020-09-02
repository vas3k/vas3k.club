import logging
from datetime import datetime, timedelta

from django.core.management import BaseCommand

from posts.models.views import PostView

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cleans up old and useless post views"

    def handle(self, *args, **options):
        day_ago = datetime.utcnow() - timedelta(days=1)
        PostView.objects.filter(unread_comments=0, registered_view_at__lte=day_ago).delete()

        # month_ago = datetime.utcnow() - timedelta(days=30)
        # PostView.objects.filter(last_view_at__lte=month_ago).delete()

        self.stdout.write("Done 🥙")
