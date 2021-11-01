import base64
import logging
from datetime import datetime, timedelta

import telegram
from django.conf import settings
from django.core.management import BaseCommand

from club.exceptions import NotFound
from notifications.digests import generate_weekly_digest
from notifications.telegram.common import send_telegram_message, CLUB_CHANNEL, render_html_message
from landing.models import GodSettings
from notifications.email.sender import send_club_email
from posts.models.post import Post
from search.models import SearchIndex
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send weekly digest"

    def add_arguments(self, parser):
        parser.add_argument("--production", nargs=1, type=bool, required=False, default=False)

    def handle(self, *args, **options):
        # render digest using a special html endpoint
        try:
            digest = generate_weekly_digest()
        except NotFound:
            log.error("Weekly digest is empty")
            return

        # get a version without "unsubscribe" footer for posting on home page
        digest_without_footer = generate_weekly_digest(no_footer=True)

        # save digest as a post
        issue = (datetime.utcnow() - settings.LAUNCH_DATE).days // 7
        year, week, _ = (datetime.utcnow() - timedelta(days=7)).isocalendar()
        post, _ = Post.objects.update_or_create(
            slug=f"{year}_{week}",
            type=Post.TYPE_WEEKLY_DIGEST,
            defaults=dict(
                author=User.objects.filter(slug="vas3k").first(),
                title=f"Клубный журнал. Итоги недели. Выпуск #{issue}",
                html=digest_without_footer,
                text=digest_without_footer,
                is_pinned_until=datetime.utcnow() + timedelta(days=1),
                is_visible=True,
                is_public=False,
            )
        )

        # make it searchable
        SearchIndex.update_post_index(post)

        # sending emails
        subscribed_users = User.objects\
            .filter(
                is_email_verified=True,
                membership_expires_at__gte=datetime.utcnow() - timedelta(days=14),
                moderation_status=User.MODERATION_STATUS_APPROVED,
            )\
            .exclude(email_digest_type=User.EMAIL_DIGEST_TYPE_NOPE)\
            .exclude(is_email_unsubscribed=True)

        for user in subscribed_users:
            self.stdout.write(f"Sending to {user.email}...")

            if not options.get("production") and user.email not in dict(settings.ADMINS).values():
                self.stdout.write("Test mode. Use --production to send the digest to all users")
                continue

            try:
                digest = digest\
                    .replace("%username%", user.slug)\
                    .replace("%user_id%", str(user.id))\
                    .replace("%secret_code%", base64.b64encode(user.secret_hash.encode("utf-8")).decode())

                send_club_email(
                    recipient=user.email,
                    subject=f"🤘 Клубный журнал. Итоги недели. Выпуск #{issue}",
                    html=digest,
                    tags=["weekly_digest", f"weekly_digest_{issue}"]
                )
            except Exception as ex:
                self.stdout.write(f"Sending to {user.email} failed: {ex}")
                log.exception(f"Error while sending an email to {user.email}")
                continue

        if options.get("production"):
            # flush digest intro and title for next time
            GodSettings.objects.update(digest_intro=None, digest_title=None)

        send_telegram_message(
            chat=CLUB_CHANNEL,
            text=render_html_message("weekly_digest_announce.html", post=post),
            disable_preview=False,
            parse_mode=telegram.ParseMode.HTML,
        )

        self.stdout.write("Done 🥙")
