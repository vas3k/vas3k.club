import re
from datetime import datetime, timedelta
from html import unescape
from math import log10
from textwrap import shorten
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.template.defaultfilters import striptags
from django.template.loader import render_to_string

from common.markdown.markdown import markdown_plain
from notifications.telegram.common import (
    Chat, NORMAL_TEXT_LIMIT, PHOTO_TEXT_LIMIT, send_telegram_image, send_telegram_message,
)
from posts.helpers import MARKDOWN_IMAGES_RE
from posts.models.post import Post


TELEGRAM_CHANNEL_ID = -1004312914852


def vas3k_rank(post, now):
    score = 3 * post.upvotes + post.comment_count
    age_seconds = (now - post.published_at).total_seconds()
    # Reddit's hot rank, relative to now: ten times the engagement offsets 12.5 hours of age.
    rank = log10(max(score, 1)) - age_seconds / 45000
    bonus = {
        Post.TYPE_POST: 0.30,
        Post.TYPE_GUIDE: 0.30,
        Post.TYPE_EVENT: 0.30,
        Post.TYPE_QUESTION: 0.10,
        Post.TYPE_THREAD: 0.10,
        Post.TYPE_LINK: 0.10,
    }.get(post.type, 0)

    if len(post.text) > 5000:
        bonus += 0.10

    if MARKDOWN_IMAGES_RE.search(post.text):
        bonus += 0.10

    # Negative ranks must also improve when a bonus is applied.
    return rank + abs(rank) * bonus


class Command(BaseCommand):
    help = "Send the hottest approved post to the test Telegram channel"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview without sending or marking the post")

    def handle(self, *args, **options):
        channel_key = str(TELEGRAM_CHANNEL_ID)

        now = datetime.utcnow()
        posts = Post.objects.filter(
            moderation_status=Post.MODERATION_APPROVED,
            visibility=Post.VISIBILITY_EVERYWHERE,
            deleted_at__isnull=True,
            published_at__gte=now - timedelta(days=3),
            published_at__lte=now,
        ).exclude(type__in=[
            Post.TYPE_REQUEST, Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST, Post.TYPE_DOCS,
        ]).select_related("room").order_by("-published_at", "id")

        ranked_posts = []

        for post in posts:
            if channel_key in (post.metadata or {}).get("is_announced_in_club_channel", {}):
                continue

            ranked_posts.append((vas3k_rank(post, now), post))

        ranked_posts.sort(key=lambda item: item[0], reverse=True)

        if not ranked_posts:
            self.stdout.write("No eligible posts in the last 3 days.")
            return

        if options["dry_run"]:
            self.stderr.write("\n".join(
                f"{rank:.3f} | +{post.upvotes} | {post.comment_count} comments | "
                f"{(now - post.published_at).total_seconds() / 3600:.1f}h | {post.title} ({post.slug})"
                for rank, post in ranked_posts
            ))

        post = ranked_posts[0][1]
        images = MARKDOWN_IMAGES_RE.findall(post.text)

        if post.image and post.type != Post.TYPE_LINK:
            images.insert(0, post.image)

        image = next((
            url for url in images
            if urlsplit(url).path.rsplit(".", 1)[-1].lower() in {"jpg", "jpeg", "png", "webp"}
        ), None)

        text = MARKDOWN_IMAGES_RE.sub("", post.text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        lead = shorten(unescape(striptags(markdown_plain(text))), width=350, placeholder="…", break_on_hyphens=False)
        message = render_to_string("notifications/telegram/channel_post_announce.html", {
            "post": post,
            "settings": settings,
            "lead": lead,
        }).strip()

        if options["dry_run"]:
            self.stdout.write(f"Image: {image or '(none)'}")
            self.stdout.write(message)
            self.stderr.write("Preview only: nothing sent to Telegram; post left unmarked.")
            return

        message_length = len(message.encode("utf-16-le")) // 2

        if message_length > NORMAL_TEXT_LIMIT:
            raise CommandError(f"Announcement for post {post.slug} exceeds Telegram's text limit; left unmarked.")

        if image and message_length <= PHOTO_TEXT_LIMIT:
            sent_message = send_telegram_image(chat=Chat(id=TELEGRAM_CHANNEL_ID), image_url=image, text=message)
        else:
            sent_message = send_telegram_message(
                chat=Chat(id=TELEGRAM_CHANNEL_ID), text=message, disable_preview=False,
            )

        if sent_message is None:
            raise CommandError(f"Telegram delivery failed for post {post.slug}; left unmarked.")

        metadata = post.metadata or {}
        announcements = metadata.setdefault("is_announced_in_club_channel", {})
        announcements[channel_key] = {
            "message_id": sent_message.message_id,
            "sent_at": datetime.utcnow().isoformat(),
        }
        Post.objects.filter(id=post.id).update(metadata=metadata)
        self.stdout.write(
            f"Sent post {post.slug} to channel {TELEGRAM_CHANNEL_ID} (message {sent_message.message_id})."
        )
