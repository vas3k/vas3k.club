from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied
from notifications.telegram.users import notify_admin_user_on_mute
from users.models.mute import UserMuted
from users.models.user import User


@require_auth
def toggle_mute(request, user_slug):
    user_to = get_object_or_404(User, slug=user_slug)
    if user_to.is_moderator or user_to == request.me:
        raise AccessDenied(
            title="Нельзя",
            message="Мьютить можно всех, кроме модераторов и себя"
        )

    total_user_muted_count = UserMuted.objects.filter(user_from=request.me).count()

    # show form on GET
    if request.method != "POST":
        is_muted = UserMuted.is_muted(
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
                "mutes_left": settings.MAX_MUTE_COUNT - total_user_muted_count,
            })

    # else — process POST
    if total_user_muted_count > settings.MAX_MUTE_COUNT:
        raise AccessDenied(
            title="Вы замьютили слишком много людей",
            message="Рекомендуем притормозить и подумать о будущем..."
        )

    comment = request.POST.get("comment") or ""
    mute, is_created = UserMuted.mute(
        user_from=request.me,
        user_to=user_to,
        comment=comment,
    )

    if is_created:
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
        deleted_count, _ = UserMuted.unmute(
            user_from=request.me,
            user_to=user_to,
        )
        
        # Verify the unmute actually worked
        if deleted_count == 0:
            # The mute record didn't exist or couldn't be deleted
            # This shouldn't happen but let's handle it gracefully
            is_still_muted = UserMuted.is_muted(
                user_from=request.me,
                user_to=user_to,
            )
            if is_still_muted:
                # Force delete with a more targeted approach
                UserMuted.objects.filter(
                    user_from=request.me,
                    user_to=user_to,
                ).delete()

        return render(request, "users/messages/unmuted.html", {
            "user": user_to,
        })


@require_auth
def muted(request, user_slug):
    if request.me.slug != user_slug:
        return HttpResponseForbidden()

    user = get_object_or_404(User, slug=user_slug)
    muted_users = UserMuted.muted_by_user(user)

    response = render(request, "users/mute/index.html", {
        "user": user,
        "muted": muted_users,
    })
    
    # Prevent caching to ensure fresh data
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response
