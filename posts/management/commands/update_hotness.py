from datetime import datetime

from django.core.management import BaseCommand
from django.db import connection

from club.settings import POST_HOTNESS_PERIOD
from posts.models.post import Post


class Command(BaseCommand):
    help = "Updates hotness rank"

    def handle(self, *args, **options):
        Post.objects.exclude(hotness=0).update(hotness=0)

        with connection.cursor() as cursor:
            cursor.execute("""
                update posts
                set hotness = coalesce(
                    (
                        select round(sum(
                            pow(
                                (%s - abs(extract(epoch from age(c.created_at, now())))) / 3600,
                                1.3
                            )
                        ))
                        from (
                            select distinct on (author_id) created_at
                            from comments
                            where comments.post_id = posts.id
                                and is_deleted = false
                                and created_at > %s
                            order by author_id
                        ) as c
                    )
                , 0.0)
                where is_visible = true
                    and last_activity_at > %s
            """, [
                POST_HOTNESS_PERIOD.total_seconds(),
                datetime.utcnow() - POST_HOTNESS_PERIOD,
                datetime.utcnow() - POST_HOTNESS_PERIOD,
            ])
