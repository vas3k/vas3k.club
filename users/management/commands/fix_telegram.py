import logging

from django.core.management import BaseCommand

from notifications.telegram.users import notify_profile_needs_review
from posts.models import Post
from users.models import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fix broken telegram admin"

    def handle(self, *args, **options):
        users = User.objects.filter(is_profile_complete=True, is_profile_reviewed=False, is_profile_rejected=False)

        for user in users:
            intro = Post.get_user_intro(user)
            notify_profile_needs_review(user, intro)

        self.stdout.write("Done 🥙")
