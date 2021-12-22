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

    # show form on GET
    if request.method != "POST":
        is_muted = Muted.is_muted(
            user_from=request.me,
            user_to=user_to,
        )
        if is_muted:
            return render(request, "users/mute/unmute.html", {
                "user": user_to,
            })
        else:
            return render(request, "users/mute/mute.html", {
                "user": user_to,
            })

    # else — POST
    total_user_mute_count = Muted.objects.filter(user_from=request.me).count()
    if total_user_mute_count > settings.MAX_MUTE_COUNT:
        raise AccessDenied(
            title="Вы замьютили слишком много юзеров",
            message="Возможно, стоит притормозить и подумать..."
        )

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
    else:
        # unmute this user
        Muted.unmute(
            user_from=request.me,
            user_to=user_to,
        )

        return render(request, "users/messages/unmuted.html", {
            "user": user_to,
        })
