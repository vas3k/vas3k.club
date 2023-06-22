import logging

from django.core.management import BaseCommand
from django.db import connection

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Move up one good old post on main page"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("""
                update posts
                set last_activity_at = now()
                where id = (
                    select id from posts
                    where published_at between now() - interval '370 day'
                    and now() - interval '350 days'
                    order by upvotes desc
                    limit 1
                )
            """)

        self.stdout.write("Done 🥙")
