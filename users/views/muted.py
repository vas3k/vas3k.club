from django.conf import settings
from django.shortcuts import get_object_or_404, render

from auth.helpers import auth_required
from notifications.telegram.users import notify_admin_user_too_many_mutes
from users.models.friends import Friend
from users.models.mute import Muted
from users.models.user import User


@auth_required
def toggle_mute(request, user_slug):
    # if request.method != "POST":
    #     raise Http404()

    user_to = get_object_or_404(User, slug=user_slug)

    mute, is_created = Muted.mute(
        user_from=request.me,
        user_to=user_to,
    )

    if is_created:
        # delete user from friends
        Friend.delete_friend(
            user_from=request.me,
            user_to=user_to,
        )

        # notify admins on too many complaints
        total_user_muted_count = Muted.objects.filter(user_to=user_to).count()
        if total_user_muted_count == settings.NOTIFY_MODERATOR_AFTER_MUTE_COUNT:
            notify_admin_user_too_many_mutes(user_to)

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
