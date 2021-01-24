from datetime import timedelta, datetime
from random import randint

from django.conf import settings
from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from common.flat_earth import parse_horoscope
from notifications.telegram.common import render_html_message
from posts.models.post import Post


def command_horo(update: Update, context: CallbackContext) -> None:
    horoscope = parse_horoscope()
    update.effective_chat.send_message(
        "Сегодня {club_day} день от сотворения Клуба, {phase_sign}\n\n{phase_description}".format(**horoscope)
    )


def command_random(update: Update, context: CallbackContext) -> None:
    post = None
    attempt = 0

    while not post and attempt < 5:
        attempt += 1
        random_date = settings.LAUNCH_DATE + timedelta(
            seconds=randint(0, int((datetime.utcnow() - settings.LAUNCH_DATE).total_seconds())),
        )

        post = Post.visible_objects() \
            .filter(published_at__lte=random_date, published_at__gte=random_date - timedelta(days=2)) \
            .filter(is_approved_by_moderator=True) \
            .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST]) \
            .order_by("?") \
            .first()

    update.effective_chat.send_message(
        render_html_message("channel_post_announce.html", post=post),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )

