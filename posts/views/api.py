from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404

from auth.helpers import api_required
from posts.models.post import Post
from bookmarks.models import PostBookmark


@api_required
def toggle_post_bookmark(request, post_slug):
    if request.method != "POST":
        raise HttpResponseNotAllowed(["POST"])

    post = get_object_or_404(Post, slug=post_slug)

    bookmark, is_created = PostBookmark.objects.get_or_create(
        user=request.me,
        post=post,
    )

    if not is_created:
        bookmark.delete()

    return JsonResponse({
        "status": "created" if is_created else "deleted"
    })
