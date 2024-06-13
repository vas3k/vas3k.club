from datetime import datetime, timedelta

from django.conf import settings
from django.shortcuts import get_object_or_404, render, redirect

from authn.decorators.auth import require_auth, require_moderator_role
from authn.models.session import Session
from club.exceptions import AccessDenied
from common.data.ban import BanReason, TEMPORARY_BAN_REASONS, PERMANENT_BAN_REASONS, PROGRESSIVE_BAN_DAYS
from common.data.hats import HATS
from notifications.email.users import send_banned_email, send_unmoderated_email, send_delete_account_confirm_email, \
    send_ping_email
from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from notifications.telegram.users import notify_admin_user_on_ban, notify_admin_user_unmoderate, notify_user_ping, \
    notify_admin_user_ping
from payments.helpers import cancel_all_stripe_subscriptions, gift_membership_days
from users.forms.admin import UserAdminForm, UserInfoAdminForm
from users.helpers import custom_ban_user, temporary_ban_user, unban_user, permanently_ban_user
from users.models.achievements import Achievement, UserAchievement
from users.models.user import User
from users.utils import is_role_manageable_by_user


@require_auth
@require_moderator_role
def admin_profile(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)

    if request.method == "POST":
        form = UserAdminForm(request.POST, request.FILES)
        if form.is_valid():
            do_user_admin_actions(request, user, form.cleaned_data)

        info_form = UserInfoAdminForm(request.POST, instance=user)
        if info_form.is_valid():
            info_form.save()

        return redirect("profile", user.slug)
    else:
        form = UserAdminForm()
        info_form = UserInfoAdminForm(instance=user)

    return render(request, "users/admin.html", {
        "user": user,
        "form": form,
        "info_form": info_form,
        "ban_progression": PROGRESSIVE_BAN_DAYS,
    })


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

    # Unban
    if data["is_unbanned"]:
        unban_user(user)

    # Temporary ban
    if data["is_temporarily_banned"]:
        reason = TEMPORARY_BAN_REASONS.get(data["temporary_ban_reason"])
        temporary_ban_user(
            user=user,
            reason=reason
        )

    # Custom ban
    if data["is_custom_banned"]:
        custom_ban_user(
            user=user,
            days=data["custom_ban_days"],
            reason=BanReason(name=data["custom_ban_name"], description=data["custom_ban_reason"], min_duration=data["custom_ban_days"])
        )

    # Permanent ban
    if data["is_permanently_banned"]:
        reason = PERMANENT_BAN_REASONS.get(data["permanent_ban_reason"])
        permanently_ban_user(
            user=user,
            reason=reason
        )

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
