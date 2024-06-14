from datetime import datetime, timedelta

from django_q.tasks import async_task

from common.data.ban import PERMANENT_BAN_DAYS, PROGRESSIVE_BAN_DAYS, BanReason
from notifications.email.users import send_banned_email
from notifications.telegram.users import notify_admin_user_on_ban, notify_user_ban
from payments.helpers import cancel_all_stripe_subscriptions
from rooms.helpers import ban_user_in_all_chats, unban_user_in_all_chats
from users.models.user import User


def temporary_ban_user(user: User, reason: BanReason):
    return custom_ban_user(
        user=user,
        days=calculate_progressive_ban_days(user, min_days=reason.min_duration),
        reason=reason
    )


def permanently_ban_user(user: User, reason: BanReason):
    cancel_all_stripe_subscriptions(user.stripe_id)
    async_task(
        ban_user_in_all_chats,
        user=user
    )

    return custom_ban_user(
        user=user,
        days=PERMANENT_BAN_DAYS,
        reason=reason
    )


def custom_ban_user(user: User, days: int, reason: BanReason) -> bool:
    if days <= 0:
        return False

    user.is_banned_until = datetime.utcnow() + timedelta(days=days)
    user.metadata = {
        **(user.metadata or {}),
        "last_ban": {
            "days": days,
            "reason": reason.name,
        }
    }
    user.save()

    # send email and other notifs
    reason_text = f"{reason.name or ''}. {reason.description or ''}" if reason.name else reason.description
    send_banned_email(user, days=days, reason=reason_text)
    notify_user_ban(user, days=days, reason=reason_text)
    notify_admin_user_on_ban(user, days=days, reason=reason_text)

    # cancel subscriptions for long bans
    if days > 60 and user.is_banned_until > user.membership_expires_at:
        cancel_all_stripe_subscriptions(user.stripe_id)

    return True


def unban_user(user: User):
    user.is_banned_until = None
    user.save()


def calculate_progressive_ban_days(user: User, min_days: int) -> int:
    # check if it's a first ban
    if not user.metadata or not user.metadata.get("last_ban"):
        return min_days

    # find next biggest number of days after last ban
    last_ban_days = int(user.metadata["last_ban"].get("days") or 0)
    for num in PROGRESSIVE_BAN_DAYS:
        if num > last_ban_days:
            return num

    # or just return the biggest one
    return PROGRESSIVE_BAN_DAYS[-1]

