import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from badges.models import UserBadge
from comments.models import Comment
from notifications.telegram.common import send_telegram_message, Chat

log = logging.getLogger(__name__)

TELEGRAM_CHANNEL_ID = -1001814814883
TIME_INTERVAL = timedelta(days=3)
SELECT_LIMIT = 40
MIN_UPVOTES = 30


class Command(BaseCommand):
    help = "Send best comments to the channel"

    def handle(self, *args, **options):
        best_comments = Comment.visible_objects().filter(
            created_at__gte=datetime.utcnow() - TIME_INTERVAL,
            post__is_approved_by_moderator=True,
            upvotes__gte=MIN_UPVOTES,
        ).order_by("-upvotes")[:SELECT_LIMIT]

        new_badges = UserBadge.objects.filter(
            created_at__gte=datetime.utcnow() - TIME_INTERVAL,
            comment__isnull=False,
        ).order_by("-created_at")[:SELECT_LIMIT]

        comments_with_badges = [b.comment for b in new_badges]

        for comment in list(best_comments) + list(comments_with_badges):
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
                    )
                except Exception as ex:
                    self.stdout.write(f"Error sending the message: {ex}")

                break

        self.stdout.write("Done 🥙")
