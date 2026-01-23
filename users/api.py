from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from authn.decorators.api import api
from badges.models import UserBadge
from club.exceptions import ApiAccessDenied
from tags.models import UserTag
from users.models.achievements import UserAchievement
from users.models.user import User


def api_profile_user(request, user_slug):
    if user_slug == "me" and request.me:
        user_slug = request.me.slug

    user = get_object_or_404(User, slug=user_slug)

    if (
        request.me.moderation_status != User.MODERATION_STATUS_APPROVED and request.me.id != user.id
    ):
        raise ApiAccessDenied(
            title="Non-approved users can only access their own profiles"
        )

    return user


@api(require_auth=True)
def api_profile(request, user_slug):
    user = api_profile_user(request, user_slug)
    scopes = request.oauth_token.get_scopes() if request.oauth_token else []
    return JsonResponse({"user": user.to_dict(include_private="contact" in scopes)})


@api(require_auth=True)
def api_profile_badge(request, user_slug):
    user = api_profile_user(request, user_slug)
    return render(request, "users/badge.html", {"user": user})


@api(require_auth=True)
def api_profile_tags(request, user_slug):
    user = api_profile_user(request, user_slug)

    allowed_groups = {"club", "tech", "hobbies", "personal", "collectible", "other"}

    user_tags = UserTag.objects.filter(user=user).select_related("tag")

    grouped_tags = {}
    for ut in user_tags:
        group = ut.tag.group
        if group in allowed_groups:
            grouped_tags.setdefault(group, []).append({
                "code": ut.tag.code,
                "name": ut.tag.name,
            })

    return JsonResponse({"tags": grouped_tags})


@api(require_auth=True)
def api_profile_achievements(request, user_slug):
    user = api_profile_user(request, user_slug)
    user_achievements = UserAchievement.objects.filter(user=user).select_related("achievement")
    return JsonResponse({"user_achievements": [ua.to_dict() for ua in user_achievements]})


@api(require_auth=True)
def api_profile_badges(request, user_slug):
    user = api_profile_user(request, user_slug)
    user_badges = UserBadge.objects.filter(user=user).select_related("badge", "from_user")
    return JsonResponse({"user_badges": [ub.to_dict() for ub in user_badges]})


@api(require_auth=True)
def api_profile_by_telegram_id(request, telegram_id):
    try:
        user = get_object_or_404(User, telegram_id=telegram_id)
    except User.MultipleObjectsReturned:
        same_telegram = list(User.objects.filter(telegram_id=telegram_id))
        same_telegram.sort(
            key=lambda user: user.moderation_status != User.MODERATION_STATUS_APPROVED,
        )
        user = same_telegram[0]

    return JsonResponse({"user": user.to_dict()})
