from telegram import Update
from telegram.ext import CallbackContext

from common.flat_earth import parse_horoscope


def command_horo(update: Update, context: CallbackContext) -> None:
    horoscope = parse_horoscope()
    update.effective_chat.send_message(
        "Сегодня {club_day} день от сотворения Клуба, {phase_sign}\n\n{phase_description}".format(**horoscope)
    )
