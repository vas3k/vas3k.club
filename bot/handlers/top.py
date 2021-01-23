from telegram import Update
from telegram.ext import CallbackContext


def command_top(update: Update, context: CallbackContext) -> None:
    update.effective_chat.send_message(
        "Топ! TODO"
    )
