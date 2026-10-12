import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management import BaseCommand
from django.template.loader import render_to_string

from badges.models import UserBadge
from comments.models import Comment
from notifications.telegram.common import send_telegram_message, Chat
from posts.models.post import Post

log = logging.getLogger(__name__)

TELEGRAM_CHANNEL_ID = -1001814814883
TIME_INTERVAL = timedelta(days=3)
SELECT_LIMIT = 40
MIN_UPVOTES = 30


class Command(BaseCommand):
    help = "Send best comments to the channel"

    def handle(self, *args, **options):
        eligible_comments = Comment.visible_objects().filter(
            is_deleted=False,
            post__moderation_status=Post.MODERATION_APPROVED,
            post__visibility=Post.VISIBILITY_EVERYWHERE,
        )
        best_comments = eligible_comments.filter(
            created_at__gte=datetime.utcnow() - TIME_INTERVAL,
            upvotes__gte=MIN_UPVOTES,
        ).order_by("-upvotes")[:SELECT_LIMIT]

        new_badges = UserBadge.objects.filter(
            created_at__gte=datetime.utcnow() - TIME_INTERVAL,
            comment_id__in=eligible_comments.order_by().values("pk"),
        ).select_related("comment__author", "comment__post").order_by("-created_at")[:SELECT_LIMIT]

        comments_with_badges = [b.comment for b in new_badges]

        for comment in list(best_comments) + list(comments_with_badges):
            if not comment.metadata or not comment.metadata.get("in_best_comments"):
                self.stdout.write(f"Comment {comment.id} +{comment.upvotes}")
                message = render_to_string("messages/best_comments.html", {
                    "comment": comment,
                    "settings": settings,
                })

                sent_message = send_telegram_message(
                    chat=Chat(id=TELEGRAM_CHANNEL_ID),
                    text=message,
                )
                if sent_message is None:
                    return
                # Failed sends remain eligible for a later run.
                comment.metadata = comment.metadata or {}
                comment.metadata["in_best_comments"] = True
                comment.save(update_fields=["metadata"])

                break

        self.stdout.write("Done 🥙")
