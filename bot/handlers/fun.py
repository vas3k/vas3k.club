from telegram import Update, ParseMode
from telegram.ext import CallbackContext

from common.flat_earth import parse_horoscope
from notifications.telegram.common import render_html_message
from posts.models.post import Post
from fun.utils import get_dayly_banek


def command_horo(update: Update, context: CallbackContext) -> None:
    horoscope = parse_horoscope()
    update.effective_chat.send_message(
        "Сегодня {club_day} день от сотворения Клуба, {phase_sign}\n\n{phase_description}".format(**horoscope)
    )


def command_banek(update: Update, context: CallbackContext) -> None:
    banek = get_dayly_banek()
    update.effective_chat.send_message(
        f"*Сегодняшний анек дня*\n\n{banek}",
        parse_mode=ParseMode.MARKDOWN,
    )


def command_random(update: Update, context: CallbackContext) -> None:
    update.effective_chat.send_message(
        render_html_message(
            "channel_post_announce.html",
            post=Post.objects.get_random_post()
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
