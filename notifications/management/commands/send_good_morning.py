import logging
from datetime import datetime, timedelta

from django.core.management import BaseCommand

from bot.common import send_telegram_message, ADMIN_CHAT, render_html_message
from posts.models import Post

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send morning digest to telegram channel"

    def handle(self, *args, **options):
        new_posts = Post.visible_objects()\
            .filter(
                is_approved_by_moderator=True,
                published_at__gte=datetime.utcnow() - timedelta(hours=24),
            )\
            .exclude(type=Post.TYPE_INTRO)\
            .order_by("-upvotes")[:7]

        send_telegram_message(
            chat=ADMIN_CHAT,
            text=render_html_message("good_morning.html", posts=new_posts),
        )

        self.stdout.write("Done 🥙")
