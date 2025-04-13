import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from posts.models.post import Post
import openai

openai.api_key = settings.OPENAI_API_KEY


class Command(BaseCommand):
    help = "Generate or update GPT-4o-mini embeddings for all posts (reindexing)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recompute and overwrite existing vectors (reindex all)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Limit the number of posts to update in one run",
        )

    def handle(self, *args, **options):
        force = options["force"]
        limit = options["limit"]

        posts = Post.visible_objects()
        if not force:
            posts = posts.filter(vector__isnull=True)

        posts = posts.order_by("-published_at")[:limit]
        total = posts.count()

        if total == 0:
            self.stdout.write("✅ Nothing to update.")
            return

        self.stdout.write(f"🚀 Updating vectors for {total} posts using {settings.OPENAI_EMBEDDINGS_MODEL}...")

        for i, post in enumerate(posts, start=1):
            try:
                if post.type == Post.TYPE_INTRO:
                    content = f"""Name: {post.author.full_name}\n\nCompany: {post.author.company} -
                    {post.author.position}\n\nFrom: {post.author.city}, {post.author.country}\n\n
                    Contacts: {post.author.bio}\n\nIntro: {post.text}"""
                else:
                    content = f"Author: {post.author.full_name}\n\nTitle: {post.title}\n\n{post.text}"

                response = openai.embeddings.create(
                    model=settings.OPENAI_EMBEDDINGS_MODEL,
                    input=content,
                )
                vector = response.data[0].embedding

                post.embeddings = vector
                with transaction.atomic():
                    post.save(update_fields=["embeddings"])

                self.stdout.write(f"✅ [{i}/{total}] Updated: {post.title[:60]}")
            except Exception as e:
                self.stdout.write(f"❌ [{i}/{total}] Failed: {post.title[:60]} — {e}")

        self.stdout.write("🎉 Done updating vectors.")
