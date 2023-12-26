from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from posts.models.post import Post
from bookmarks.models import PostBookmark


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_post_bookmark(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    bookmark, is_created = PostBookmark.objects.get_or_create(
        user=request.me,
        post=post,
    )

    if not is_created:
        bookmark.delete()

    return {
        "status": "created" if is_created else "deleted"
    }
