import logging
from datetime import datetime, timedelta

from django.core.management import BaseCommand

from posts.models.views import PostView

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Updates hotness rank"

    def handle(self, *args, **options):


        day_ago = datetime.utcnow() - timedelta(days=1)
        PostView.objects.filter(unread_comments=0, registered_view_at__lte=day_ago).delete()

        self.stdout.write("Done 🥙")
