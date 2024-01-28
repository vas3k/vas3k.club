from telegram import Bot, ParseMode

from askbot.models import UserAskBan
from club import settings
from users.models.user import User


def send_html_msg(chat_id: int, text: str, reply_to_message_id: int = None):
    bot = Bot(token=settings.TELEGRAM_ASK_BOT_TOKEN)
    return bot.send_message(chat_id=chat_id, text=text, reply_to_message_id=reply_to_message_id,
                     parse_mode=ParseMode.HTML)


def is_banned(user: User) -> bool:
    user_ask_ban = UserAskBan.objects.filter(user=user).first()
    return user_ask_ban and user_ask_ban.is_banned


def channel_msg_link(message_id: str) -> str:
    channel_link_id = str(settings.TELEGRAM_ASK_BOT_QUESTION_CHANNEL_ID).replace("-100", "")
    return chat_msg_link(channel_link_id, message_id)


def chat_msg_link(chat_id: str, message_id: str) -> str:
    return f"https://t.me/c/{chat_id}/{message_id}"
