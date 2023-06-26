import logging
import random
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.db.models import Q

from posts.models.post import Post

log = logging.getLogger(__name__)


DELTA_DAYS = 5


class Command(BaseCommand):
    help = "Move up one good old post on main page"

    def handle(self, *args, **options):
        now = datetime.utcnow()
        days_since_launch_date = (now - settings.LAUNCH_DATE).days
        random_day_in_the_past = random.randint(200, days_since_launch_date)

        random_good_post = Post.visible_objects()\
            .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST])\
            .filter(Q(is_approved_by_moderator=True) | Q(upvotes__gte=settings.COMMUNITY_APPROVE_UPVOTES))\
            .filter(
                published_at__gte=now - timedelta(days=random_day_in_the_past + DELTA_DAYS),
                published_at__lte=now - timedelta(days=random_day_in_the_past - DELTA_DAYS),
             )\
            .order_by("-upvotes")\
            .first()

        self.stdout.write(f"Promoting post '{random_good_post.title}'")

        random_good_post.last_activity_at = datetime.utcnow()
        random_good_post.save()

        self.stdout.write("Done 🥙")
