from django.template.loader import render_to_string

from badges.models import UserBadge
from users.models.user import User


def badge_generator(request, admin_page):
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

    return render_to_string("godmode/pages/badge_generator.html", {
        "users": users,
        "requested_users": ",".join(requested_users),
        "hide_bio": request.GET.get("hide_bio"),
        "hide_stats": request.GET.get("hide_stats"),
        "hide_badges": request.GET.get("hide_badges"),
        "repeat": repeat,
    }, request=request)

