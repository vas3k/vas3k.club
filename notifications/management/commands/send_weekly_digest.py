import logging
from datetime import datetime, timedelta

import requests
from django.conf import settings
from django.core.management import BaseCommand
from django.urls import reverse

from landing.models import GodSettings
from notifications.email.sender import send_club_email
from posts.models import Post
from users.models import User

log = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send weekly digest to subscribers"

    def handle(self, *args, **options):
        # render digest using a special html endpoint
        digest_url = "https://vas3k.club" + reverse("render_weekly_digest")
        self.stdout.write(f"Generating digest: {digest_url}")

        digest_html_response = requests.get(digest_url)
        if digest_html_response.status_code > 400:
            log.error("Weekly digest error: bad status code", extra={"html": digest_html_response.text})
            return

        digest_html = digest_html_response.text

        # save digest as a post
        issue = (datetime.utcnow() - settings.LAUNCH_DATE).days // 7
        year, week, _ = (datetime.utcnow() - timedelta(days=7)).isocalendar()
        Post.objects.update_or_create(
            slug=f"{year}_{week}",
            type=Post.TYPE_WEEKLY_DIGEST,
            defaults=dict(
                author=User.objects.filter(slug="vas3k").first(),
                title=f"Клубный журнал. Итоги недели. Выпуск #{issue}",
                html=digest_html,
                text=digest_html,
                is_pinned_until=datetime.utcnow() + timedelta(days=1),
                is_visible=True,
                is_public=False,
            )
        )

        # sending emails
        subscribed_users = User.objects\
            .filter(
                is_email_verified=True,
                membership_expires_at__gte=datetime.utcnow() - timedelta(days=14)
            )\
            .exclude(email_digest_type=User.EMAIL_DIGEST_TYPE_NOPE)\
            .exclude(is_profile_rejected=True)\
            .exclude(is_email_unsubscribed=True)

        for user in subscribed_users:
            self.stdout.write(f"Sending to {user.email}...")

            # if settings.DEBUG and user.email != "me@vas3k.ru":
            #     continue

            try:
                user_digest_html = str(digest_html)
                user_digest_html = user_digest_html\
                    .replace("%username%", user.slug)\
                    .replace("%user_id%", str(user.id))\
                    .replace("%secret_code%", user.secret_hash)

                send_club_email(
                    recipient=user.email,
                    subject=f"🤘 Клубный журнал. Итоги недели. Выпуск #{issue}",
                    html=user_digest_html,
                    tags=["weekly_digest", f"weekly_digest_{issue}"]
                )
            except Exception as ex:
                self.stdout.write(f"Sending to {user.email} failed: {ex}")
                log.exception(f"Error while sending an email to {user.email}")
                continue

        # flush digest intro for next time
        GodSettings.objects.update(digest_intro=None)

        self.stdout.write("Done 🥙")
