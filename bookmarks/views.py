from django.shortcuts import render

from authn.decorators.auth import require_auth
from bookmarks.helpers import get_user_bookmarks
from common.pagination import paginate


@require_auth
def bookmarks(request):
    posts = get_user_bookmarks(request.me)

    return render(request, "bookmarks.html", {
        "posts": paginate(request, posts),
    })
