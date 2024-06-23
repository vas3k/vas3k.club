from django.conf import settings
from django.core.management import BaseCommand

import utils.manticore
from posts.models.post import Post
from utils.queryset import chunked_queryset


class Command(BaseCommand):
    help = "Наполнение индекса manticore"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            return self.stdout.write("☢️  Только для запуска в DEBUG режиме")

        indexed_post_count = 0

        for chunk in chunked_queryset(
            Post.visible_objects().filter(is_shadow_banned=False)
        ):
            for post in chunk:
                self.stdout.write(f"Indexing post: {post.slug}")
                utils.manticore.replace("posts", post)
                indexed_post_count += 1

