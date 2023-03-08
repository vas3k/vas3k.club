from django.http import Http404
from django.shortcuts import get_object_or_404

from authn.decorators.api import api
from comments.models import Comment
from posts.models.post import Post


@api(require_auth=True)
def api_list_post_comments(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if not post.can_view(request.me):
        raise Http404()

    comments = Comment.visible_objects().filter(post=post)

    return {
        "comments": [comment.to_dict() for comment in comments]
    }
