from django.template.loader import render_to_string
from telegram import LinkPreviewOptions, Update
from telegram.constants import ChatMemberStatus, ChatType, ParseMode
from telegram.ext import CallbackContext

from bot.decorators import ensure_fresh_db_connection
from club import settings
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


@ensure_fresh_db_connection
async def welcome_member(update: Update, context: CallbackContext) -> None:
    membership = update.chat_member
    old_member = membership.old_chat_member
    member = membership.new_chat_member

    if membership.chat.type not in {ChatType.GROUP, ChatType.SUPERGROUP} or member.user.is_bot:
        return

    member_statuses = {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER}
    was_member = old_member.status in member_statuses or (
        old_member.status == ChatMemberStatus.RESTRICTED and old_member.is_member
    )
    is_member = member.status in member_statuses or (
        member.status == ChatMemberStatus.RESTRICTED and member.is_member
    )

    if was_member or not is_member:
        return

    if not Room.objects.filter(chat_id=str(membership.chat.id)).exists():
        return

    user = User.objects.filter(telegram_id=str(member.user.id)).first()
    actor = membership.from_user
    # Link creators and join-request approvers are not necessarily personal inviters.
    directly_invited = actor.id != member.user.id and not actor.is_bot and not (
        membership.invite_link or membership.via_join_request or membership.via_chat_folder_invite_link
    )
    inviter = User.objects.filter(telegram_id=str(actor.id)).first() if directly_invited else None

    if user:
        template = "chat_welcome.html"
    elif not directly_invited:
        template = "chat_welcome_unknown.html"
    elif inviter:
        template = "chat_welcome_invited.html"
    else:
        template = "chat_welcome_unknown_inviter.html"

    data = {
        "user": user,
        "telegram_user": member.user,
        "inviter": inviter,
        "telegram_inviter": actor if directly_invited else None,
        "settings": settings,
    }
    await context.bot.send_message(
        chat_id=membership.chat.id,
        text=render_to_string(f"notifications/telegram/membership/{template}", data).strip(),
        parse_mode=ParseMode.HTML,
        link_preview_options=LinkPreviewOptions(is_disabled=True),
    )
