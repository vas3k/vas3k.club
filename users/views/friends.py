from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.conf import settings
from django.views.decorators.http import require_http_methods

from authn.decorators.auth import require_auth
from authn.decorators.api import api
from common.pagination import paginate
from users.models.friends import Friend
from users.models.user import User


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_friend(request, user_slug):
    if request.method != "POST":
        raise Http404()

    user_to = get_object_or_404(User, slug=user_slug)

    friend, is_created = Friend.add_friend(
        user_from=request.me,
        user_to=user_to,
    )

    if not is_created:
        Friend.delete_friend(
            user_from=request.me,
            user_to=user_to,
        )

    return {
        "status": "created" if is_created else "deleted",
    }


@require_auth
def friends(request, user_slug):
    if request.me.slug != user_slug:
        return HttpResponseForbidden()

    user = get_object_or_404(User, slug=user_slug)

    user_friends = Friend.user_friends(user_from=user)

    return render(request, "users/friends/index.html", {
        "user": user,
        "friends_paginated": paginate(request, user_friends, page_size=settings.FRIENDS_PAGE_SIZE)
    })
