import base64
import logging
from datetime import datetime, timedelta

import telegram
from django.conf import settings
from django.core.management import BaseCommand

from club.exceptions import NotFound
from godmode.models import ClubSettings
from notifications.digests import generate_weekly_digest
from notifications.telegram.common import send_telegram_message, CLUB_CHANNEL, render_html_message, Chat
from notifications.email.sender import send_mass_email
from posts.models.post import Post
from search.models import SearchIndex
from users.models.user import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send weekly digest"

    def add_arguments(self, parser):
        parser.add_argument("--production", nargs=1, type=bool, required=False, default=False)

    def handle(self, *args, **options):
        try:
            digest_template, _ = generate_weekly_digest()
        except NotFound:
            log.error("Weekly digest is empty")
            return

        # get a version without "unsubscribe" footer for posting on home page
        digest_without_footer, og_description = generate_weekly_digest(no_footer=True)

        # get title and description
        digest_title = ClubSettings.get("digest_title")
        digest_intro = ClubSettings.get("digest_intro")

        # save digest as a post
        issue = (datetime.utcnow() - settings.LAUNCH_DATE).days // 7
        year, week, _ = (datetime.utcnow() - timedelta(days=7)).isocalendar()
        post, _ = Post.objects.update_or_create(
            slug=f"{year}_{week}",
            type=Post.TYPE_WEEKLY_DIGEST,
            defaults=dict(
                author=User.objects.filter(slug="vas3k").first(),
                title=f"Клубный журнал. Выпуск #{issue}: {digest_title}",
                html=digest_without_footer,
                text=digest_without_footer,
                is_pinned_until=datetime.utcnow() + timedelta(days=1),
                moderation_status=Post.MODERATION_APPROVED,
                visibility=Post.VISIBILITY_EVERYWHERE,
                metadata={"og_description": og_description},
                is_public=False,
            )
        )

        # make it searchable
        SearchIndex.update_post_index(post)

        # sending telegrams
        telegram_subscribers = User.objects\
            .exclude(
                email_digest_type=User.EMAIL_DIGEST_TYPE_NOPE
            )\
            .filter(
                membership_expires_at__gte=datetime.utcnow() - timedelta(days=30),
                moderation_status=User.MODERATION_STATUS_APPROVED,
                telegram_id__isnull=False,
            )

        for user in telegram_subscribers:
            if user.telegram_id:
                send_telegram_message(
                    chat=Chat(id=user.telegram_id),
                    text=render_html_message(
                        "weekly_digest_announce.html",
                        post=post,
                        issue_number=issue,
                        digest_title=digest_title,
                        digest_intro=digest_intro,
                        include_unsubscribe=True,
                    ),
                    disable_preview=False,
                    parse_mode=telegram.ParseMode.HTML,
                )

        # sending emails
        email_subscribers = User.objects\
            .filter(
                is_email_verified=True,
                membership_expires_at__gte=datetime.utcnow() - timedelta(days=14),
                moderation_status=User.MODERATION_STATUS_APPROVED,
            )\
            .exclude(email_digest_type=User.EMAIL_DIGEST_TYPE_NOPE)\
            .exclude(is_email_unsubscribed=True)

        for user in email_subscribers:
            self.stdout.write(f"Sending to {user.email}...")

            if not options.get("production") and not user.is_god:
                continue

            try:
                secret_code = base64.b64encode(user.secret_hash.encode("utf-8")).decode()

                digest = digest_template\
                    .replace("%username%", user.slug)\
                    .replace("%user_id%", str(user.id))\
                    .replace("%secret_code%", secret_code)

                send_mass_email(
                    recipient=user.email,
                    subject=f"✖︎ Клубный журнал #{issue}. {digest_title}",
                    html=digest,
                    unsubscribe_link=f"{settings.APP_HOST}/notifications/unsubscribe/{user.id}/{secret_code}/"
                )
            except Exception as ex:
                self.stdout.write(f"Sending to {user.email} failed: {ex}")
                log.exception(f"Error while sending an email to {user.email}")
                continue

        if options.get("production"):
            # announce on channel
            send_telegram_message(
                chat=CLUB_CHANNEL,
                text=render_html_message(
                    "weekly_digest_announce.html",
                    post=post,
                    issue_number=issue,
                    digest_title=digest_title,
                    digest_intro=digest_intro
                ),
                disable_preview=False,
                parse_mode=telegram.ParseMode.HTML,
            )

            # flush digest intro and title for next time
            ClubSettings.set("digest_title", None)
            ClubSettings.set("digest_intro", None)

        self.stdout.write("Done 🥙")
