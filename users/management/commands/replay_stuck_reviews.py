import logging

from django.core.management import BaseCommand

from notifications.telegram.users import notify_profile_needs_review
from posts.models.post import Post
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fix broken or stuck review messages"

    def handle(self, *args, **options):
        users = User.objects.filter(moderation_status=User.MODERATION_STATUS_ON_REVIEW)

        for user in users:
            intro = Post.get_user_intro(user)
            notify_profile_needs_review(user, intro)

        self.stdout.write("Done 🥙")
