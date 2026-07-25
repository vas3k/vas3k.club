import logging
from datetime import datetime, timedelta

from telegram.error import TelegramError

from notifications.telegram.bot import bot
from rooms.models import Room
from users.models.user import User

log = logging.getLogger(__name__)

ACTIVE_CHAT_MEMBER_STATUSES = {"creator", "administrator", "member", "restricted"}


def get_user_chats(user: User) -> list[Room]:
    if not user.telegram_id:
        return []

    chats = []
    for room in Room.objects.filter(chat_id__isnull=False):
        try:
            chat_member = bot.get_chat_member(room.chat_id, user.telegram_id)
            if chat_member and chat_member.status in ACTIVE_CHAT_MEMBER_STATUSES:
                chats.append(room)
        except TelegramError as ex:
            log.warning(f"Failed to get user {user.slug} in chat {room.slug}: {ex}")

    return chats


def ban_user_in_all_chats(user: User, is_permanent=True):
    if not user.telegram_id:
        log.warning(f"User {user.slug} has no telegram_id, can't ban")
        return

    until_date = None if is_permanent else datetime.utcnow() + timedelta(minutes=5)

    for room in Room.objects.filter(chat_id__isnull=False):
        try:
            chat_member = bot.get_chat_member(room.chat_id, user.telegram_id)
            if chat_member:
                is_ok = bot.ban_chat_member(
                    room.chat_id,
                    user.telegram_id,
                    until_date=until_date,
                )
                if is_ok:
                    log.info(f"User {user.slug} banned in chat {room.slug}")
        except TelegramError as ex:
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
        except TelegramError as ex:
            log.warning(f"Can't unban user {user.slug} in chat {room.slug}: {ex}")


def print_user_in_all_chats(user: User, is_permanent=True):
    if not user.telegram_id:
        log.warning(f"User {user.slug} has no telegram_id, can't ban")
        return

    for room in get_user_chats(user):
        print(f"✅ User found is in chat «{room.title}»")
