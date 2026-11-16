from telegram import Update
from telegram.constants import ChatMemberStatus
from telegram.ext import CallbackContext

from bot.decorators import ensure_fresh_db_connection
from rooms.models import Room, RoomSubscription
from users.models.user import User


@ensure_fresh_db_connection
async def chat_membership(update: Update, context: CallbackContext) -> None:
    membership = update.chat_member
    member = membership.new_chat_member

    if member.user.is_bot:
        return

    user = User.objects.filter(telegram_id=str(member.user.id)).first()

    if not user:
        return

    is_member = member.status in {
        ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER,
    } or (member.status == ChatMemberStatus.RESTRICTED and member.is_member)

    for room in Room.objects.filter(chat_id=str(membership.chat.id)):
        if is_member:
            RoomSubscription.join_chat(user=user, room=room)
        else:
            RoomSubscription.leave_chat(user=user, room=room)
