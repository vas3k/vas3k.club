from django.shortcuts import render

from auth.helpers import auth_required
from common.pagination import paginate
from posts.models import Post


@auth_required
def bookmarks(request):
    user = request.me

    posts = Post.objects.filter(bookmarks__user=user).order_by('-bookmarks__created_at').all()

    return render(request, "bookmarks.html", {
        "posts": paginate(request, posts),
    })
