from django.shortcuts import render

from auth.helpers import auth_required
from common.pagination import paginate
from posts.models.post import Post


@auth_required
def bookmarks(request):
    user = request.me

    posts = Post.objects_for_user(user)\
        .filter(bookmarks__user=user, deleted_at__isnull=True)\
        .order_by('-bookmarks__created_at')\
        .all()

    return render(request, "bookmarks.html", {
        "posts": paginate(request, posts),
    })
