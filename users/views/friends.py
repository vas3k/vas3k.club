from django.shortcuts import render, redirect
from django.conf import settings

from authn.decorators.auth import require_auth
from common.pagination import paginate
from users.models.friends import Friend


@require_auth
def friends(request, user_slug):
    if request.me.slug != user_slug:
        return redirect("friends", user_slug=request.me.slug, permanent=False)

    user_friends = Friend.user_friends(user_from=request.me)

    return render(request, "users/friends/index.html", {
        "user": request.me,
        "friends_paginated": paginate(request, user_friends, page_size=settings.FRIENDS_PAGE_SIZE)
    })
