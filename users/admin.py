from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import redirect

from auth.models import Session
from club.exceptions import AccessDenied
from common.data.hats import HATS
from notifications.email.users import send_unmoderated_email, send_banned_email, send_ping_email, \
    send_delete_account_confirm_email
from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from notifications.telegram.users import notify_user_ping, notify_admin_user_ping, notify_admin_user_unmoderate, \
    notify_admin_user_on_ban
from payments.helpers import cancel_all_stripe_subscriptions, gift_membership_days
from users.models.achievements import UserAchievement, Achievement
from users.models.user import User
from users.utils import is_role_manageable_by_user


def do_user_admin_actions(request, user, data):
    if not request.me.is_moderator:
        raise AccessDenied()

    # Roles
    if data["role"] and is_role_manageable_by_user(data["role"], request.me):
        role = data["role"]
        if data["role_action"] == "add" and role not in user.roles:
            user.roles.append(role)
            user.save()
        if data["role_action"] == "delete" and role in user.roles:
            user.roles.remove(role)
            user.save()

    # Hats
    if data["remove_hat"]:
        user.hat = None
        user.save()

    if data["add_hat"]:
        if data["new_hat"]:
            hat = HATS.get(data["new_hat"])
            if hat:
                user.hat = {"code": data["new_hat"], **hat}
                user.save()
        else:
            user.hat = {
                "code": "custom",
                "title": data["new_hat_name"],
                "icon": data["new_hat_icon"],
                "color": data["new_hat_color"],
            }
            user.save()

    # Achievements
    if data["new_achievement"]:
        achievement = Achievement.objects.filter(code=data["new_achievement"]).first()
        if achievement:
            UserAchievement.objects.get_or_create(
                user=user,
                achievement=achievement,
            )

    # Ban
    if data["is_banned"]:
        if not user.is_god:
            user.is_banned_until = datetime.utcnow() + timedelta(days=data["ban_days"])
            user.save()
            if data["ban_days"] > 0:
                send_banned_email(user, days=data["ban_days"], reason=data["ban_reason"])
                notify_admin_user_on_ban(user, days=data["ban_days"], reason=data["ban_reason"])

    # Unmoderate
    if data["is_rejected"]:
        user.moderation_status = User.MODERATION_STATUS_REJECTED
        user.save()
        send_unmoderated_email(user)
        notify_admin_user_unmoderate(user)

    # Delete account
    if data["delete_account"] and request.me.is_god:
        user.membership_expires_at = datetime.utcnow()
        user.is_banned_until = datetime.utcnow() + timedelta(days=5000)

        # cancel recurring payments
        cancel_all_stripe_subscriptions(user.stripe_id)

        # mark user for deletion
        user.deleted_at = datetime.utcnow()
        user.save()

        # remove sessions
        Session.objects.filter(user=user).delete()

        # notify user
        send_delete_account_confirm_email(
            user=user,
        )

        # notify admins
        send_telegram_message(
            chat=ADMIN_CHAT,
            text=f"💀 Юзер был удален админами: {settings.APP_HOST}/user/{user.slug}/",
        )

    # Ping
    if data["ping"]:
        send_ping_email(user, message=data["ping"])
        notify_user_ping(user, message=data["ping"])
        notify_admin_user_ping(user, message=data["ping"])

    # Add more days of membership
    if data["add_membership_days"] and int(data["add_membership_days"]) > 0:
        gift_membership_days(
            days=data["add_membership_days"],
            from_user=request.me,
            to_user=user,
            deduct_from_original_user=False,
        )

        send_telegram_message(
            chat=ADMIN_CHAT,
            text=f"🎁 <b>Юзеру {user.slug} добавили {data['add_membership_days']} дней членства</b>",
        )

    return redirect("profile", user.slug)
