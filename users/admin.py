from datetime import datetime, timedelta

from django.shortcuts import redirect

from club.exceptions import AccessDenied
from common.data.hats import HATS
from notifications.email.users import send_unmoderated_email, send_banned_email, send_ping_email
from notifications.telegram.users import notify_user_ping
from users.models.achievements import UserAchievement, Achievement
from users.models.user import User


def do_user_admin_actions(request, user, data):
    if not request.me.is_moderator:
        raise AccessDenied()

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
            send_banned_email(user, days=data["ban_days"], reason=data["ban_reason"])

    # Unban
    if data["is_unbanned"]:
        user.is_banned_until = None
        user.save()

    # Unmoderate
    if data["is_rejected"]:
        user.moderation_status = User.MODERATION_STATUS_REJECTED
        user.save()
        send_unmoderated_email(user)

    # Ping
    if data["ping"]:
        send_ping_email(user, message=data["ping"])
        notify_user_ping(user, message=data["ping"])

    return redirect("profile", user.slug)
