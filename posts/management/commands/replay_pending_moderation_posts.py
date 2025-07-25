import logging

from django.core.management import BaseCommand

from notifications.telegram.posts import send_published_post_to_moderators
from notifications.telegram.users import notify_profile_needs_review
from posts.models.post import Post
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send pending moderation posts to moderators again"

    def handle(self, *args, **options):
        posts = Post.objects.filter(moderation_status=Post.MODERATION_PENDING)

        for post in posts:
            send_published_post_to_moderators(post=post)

        self.stdout.write("Done 🥙")
