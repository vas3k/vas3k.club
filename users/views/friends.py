from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from django.views.decorators.http import require_http_methods

from authn.decorators.auth import require_auth
from authn.decorators.api import api
from common.pagination import paginate
from users.models.friends import Friend
from users.models.user import User


@api(require_auth=True)
@require_http_methods(["GET", "POST"])
def api_friend(request, user_slug):
    user_to = get_object_or_404(User, slug=user_slug)

    if request.method == "GET":
        friend = Friend.user_friends(request.me).filter(user_to=user_to).first()
        if not friend:
            raise Http404()

        return {
            "friend": friend.to_dict()
        }

    if request.method == "POST":
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
        return redirect("friends", user_slug=request.me.slug, permanent=False)

    user_friends = Friend.user_friends(user_from=request.me)

    return render(request, "users/friends/index.html", {
        "user": request.me,
        "friends_paginated": paginate(request, user_friends, page_size=settings.FRIENDS_PAGE_SIZE)
    })
