import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from comments.models import Comment
from notifications.telegram.common import send_telegram_message, Chat

log = logging.getLogger(__name__)

TELEGRAM_CHANNEL_ID = -1001814814883
TIME_INTERVAL = timedelta(days=3)
LIMIT = 20
MIN_UPVOTES = 25


class Command(BaseCommand):
    help = "Send best comments to the channel"

    def handle(self, *args, **options):
        best_comments = Comment.visible_objects().filter(
            created_at__gte=datetime.utcnow() - TIME_INTERVAL,
            post__is_approved_by_moderator=True,
            upvotes__gte=MIN_UPVOTES,
        ).order_by("-upvotes")[:LIMIT]

        for comment in best_comments:
            if not comment.metadata or not comment.metadata.get("in_best_comments"):
                self.stdout.write(f"Comment {comment.id} +{comment.upvotes}")
                comment.metadata = comment.metadata or {}
                comment.metadata["in_best_comments"] = True
                comment.save()

                message = render_to_string("messages/best_comments.html", {
                    "comment": comment,
                    "settings": settings,
                })

                try:
                    send_telegram_message(
                        chat=Chat(id=TELEGRAM_CHANNEL_ID),
                        text=message,
                        disable_preview=False,
                    )
                except Exception as ex:
                    self.stdout.write(f"Error sending the message: {ex}")

                break

        self.stdout.write("Done 🥙")
