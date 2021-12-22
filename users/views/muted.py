from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from auth.helpers import auth_required
from club.exceptions import AccessDenied
from notifications.telegram.users import notify_admin_user_on_mute
from users.models.friends import Friend
from users.models.mute import Muted
from users.models.user import User


@auth_required
def toggle_mute(request, user_slug):
    user_to = get_object_or_404(User, slug=user_slug)
    if user_to.is_curator or user_to.is_moderator:
        raise AccessDenied(title="У этого юзера иммунитет от мьюта")

    total_user_mute_count = Muted.objects.filter(user_from=request.me).count()
    if total_user_mute_count > settings.MAX_MUTE_COUNT:
        raise AccessDenied(
            title="Вы замьютили слишком много юзеров",
            message="Возможно, стоит притормозить и подумать..."
        )

    if request.method != "POST":
        return render(request, "users/mute.html", {
            "user": user_to,
        })

    comment = request.POST.get("comment") or ""
    mute, is_created = Muted.mute(
        user_from=request.me,
        user_to=user_to,
        comment=comment,
    )

    if is_created:
        # delete user from friends
        Friend.delete_friend(
            user_from=request.me,
            user_to=user_to,
        )

        # notify admins
        notify_admin_user_on_mute(
            user_from=request.me,
            user_to=user_to,
            comment=comment,
        )

        return render(request, "users/messages/muted.html", {
            "user": user_to,
        })

    Muted.unmute(
        user_from=request.me,
        user_to=user_to,
    )

    return render(request, "users/messages/unmuted.html", {
        "user": user_to,
    })
