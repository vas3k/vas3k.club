import logging

import telegram

from notifications.telegram.bot import bot
from rooms.models import Room
from users.models.user import User

log = logging.getLogger(__name__)


def ban_user_in_all_chats(user: User):
    if not user.telegram_id:
        log.warning(f"User {user.slug} has no telegram_id, can't ban")
        return

    for room in Room.objects.filter(chat_id__isnull=False):
        try:
            chat_member = bot.get_chat_member(room.chat_id, user.telegram_id)
            if chat_member:
                is_ok = bot.kick_chat_member(room.chat_id, user.telegram_id)
                if is_ok:
                    log.info(f"User {user.slug} banned in chat {room.slug}")
        except telegram.TelegramError as ex:
            log.warning(f"Failed to ban user {user.slug} in chat {room.slug}: {ex}")


def unban_user_in_all_chats(user: User):
    if not user.telegram_id:
        log.warning(f"User {user.slug} has no telegram_id, can't unban")
        return

    for room in Room.objects.filter(chat_id__isnull=False):
        try:
            is_ok = bot.unban_chat_member(room.chat_id, user.telegram_id)
            if is_ok:
                log.info(f"User {user.slug} unbanned in chat {room.slug}")
        except telegram.TelegramError as ex:
            log.warning(f"Can't unban user {user.slug} in chat {room.slug}: {ex}")
