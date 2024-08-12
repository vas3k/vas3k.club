from django.http import Http404
from django.shortcuts import render, get_object_or_404

from authn.decorators.auth import require_auth
from badges.models import UserBadge
from club.exceptions import BadRequest
from users.models.notes import UserNote
from users.models.user import User
from users.models.achievements import Achievement


@require_auth
def badge_generator(request):
    requested_users = request.GET.get("users")
    if requested_users:
        requested_users = requested_users.split(",")
    else:
        requested_users = [request.me.slug]

    users = User.registered_members().filter(slug__in=requested_users)

    for user in users:
        user.badges = UserBadge.user_badges_grouped(user=user)

    repeat = int(request.GET.get("repeat") or 1)
    if repeat > 1:
        users = [u for u in users for _ in range(repeat)]

    # sort by name
    users = sorted(users, key=lambda u: u.full_name.lower())

    return render(request, "misc/badge_generator.html", {
        "users": users,
        "requested_users": ",".join(requested_users),
        "hide_bio": request.GET.get("hide_bio"),
        "hide_stats": request.GET.get("hide_stats"),
        "hide_badges": request.GET.get("hide_badges"),
        "repeat": repeat,
    })


@require_auth
def mass_note(request):
    # select users with specific achievement
    achievement_code = request.GET.get("achievement_code")
    achievement = None
    if achievement_code:
        achievement = get_object_or_404(Achievement, code=achievement_code)
        if not achievement.is_visible:
            raise Http404()

    # or select users by a list of slugs
    handpicked_users = request.GET.get("handpicked_users")
    if handpicked_users:
        users = User.registered_members().filter(slug__in=[slug.strip() for slug in handpicked_users.split(",")])
    elif achievement:
        users = User.registered_members().filter(achievements__achievement_id=achievement.code)
    else:
        users = []

    # now do actual job!
    if request.method == "POST":
        users = request.POST.get("users")
        users = User.registered_members()\
            .filter(slug__in=[slug.strip() for slug in users.split(",")])\
            .exclude(id=request.me.id)

        if not users:
            raise BadRequest(
                title="Нет таких юзеров :(",
                message="Пожалуйста, укажите хотя бы одного существующего пользователя, кроме себя",
            )

        # "note" might be empty, in this case we simply remove it
        note = request.POST.get("note")
        if note:
            note = note.strip()

        only_new = request.POST.get("only_new")

        updated_users = []

        for user in users:
            if not note:
                UserNote.objects.filter(
                    user_from=request.me,
                    user_to=user
                ).delete()
                updated_users += [user]
            elif only_new:
                _, is_created = UserNote.objects.get_or_create(
                    user_from=request.me,
                    user_to=user,
                    defaults=dict(
                        text=note
                    )
                )
                if is_created:
                    updated_users += [user]
            else:
                UserNote.objects.update_or_create(
                    user_from=request.me,
                    user_to=user,
                    defaults=dict(
                        text=note
                    )
                )
                updated_users += [user]

        return render(request, "misc/mass_note.html", {
            "users": users,
            "updated_users": updated_users,
            "achievement": achievement,
            "note": note,
            "status": "done",
        })

    return render(request, "misc/mass_note.html", {
        "users": users,
        "achievement": achievement,
        "custom_note": request.GET.get("custom_note"),
        "achievements": Achievement.objects.filter(is_visible=True),
    })
