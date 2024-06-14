from notifications.telegram.bot import bot
from rooms.models import Room
from users.models.user import User


def ban_user_in_all_chats(user: User):
    if not user.telegram_id:
        return

    for room in Room.objects.filter(chat_id__isnull=False):
        bot.kick_chat_member(room.chat_id, user.telegram_id)


def unban_user_in_all_chats(user: User):
    if not user.telegram_id:
        return

    for room in Room.objects.filter(chat_id__isnull=False):
        bot.unban_chat_member(room.chat_id, user.telegram_id)
