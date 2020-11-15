from datetime import datetime

from django.db import connection

from club.settings import POST_HOTNESS_PERIOD
from posts.models.post import Post


def update_post_hotness():
    Post.objects.exclude(hotness=0).update(hotness=0)

    with connection.cursor() as cursor:
        cursor.execute("""
            update posts
            set hotness = (
                select round(sum(
                    pow(
                        (%s - abs(extract(epoch from age(created_at, now())))) / 3600,
                        1.3
                    )
                ))
                from comments
                where comments.post_id = posts.id
                    and is_deleted = false
                    and created_at > %s
            )
            where is_visible = true
                and last_activity_at > %s
        """, [
            POST_HOTNESS_PERIOD.total_seconds(),
            datetime.utcnow() - POST_HOTNESS_PERIOD,
            datetime.utcnow() - POST_HOTNESS_PERIOD,
        ])
