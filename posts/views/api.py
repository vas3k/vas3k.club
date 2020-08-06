from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404

from auth.helpers import api_required
from posts.models import Post, PostFavourite


@api_required
def toggle_post_favourite(request, post_slug):
    if request.method != "POST":
        raise HttpResponseNotAllowed(["POST"])

    post = get_object_or_404(Post, slug=post_slug)

    favourite, is_created = PostFavourite.objects.get_or_create(
        user=request.me,
        post=post,
    )

    if not is_created:
        favourite.delete()

    return JsonResponse({
        "status": "created" if is_created else "deleted"
    })
