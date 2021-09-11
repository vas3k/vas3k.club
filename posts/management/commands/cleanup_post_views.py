import logging

from django.core.management import BaseCommand
from django.db import connection

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cleans up old and useless post views and history to save DB space"

    def handle(self, *args, **options):
        # cleanup anonymous post_views older than 3 days
        with connection.cursor() as cursor:
            cursor.execute("""
                delete from post_views where user_id is null and last_view_at < now() - interval '3 days'
            """)

        # cleanup editing history after 1 month
        with connection.cursor() as cursor:
            cursor.execute("""
                delete from posts_history where history_date <= now() - interval '3 month'
            """)
            cursor.execute("""
                delete from comments_history where history_date <= now() - interval '3 month'
            """)

        self.stdout.write("Done 🥙")
