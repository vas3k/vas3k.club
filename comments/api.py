from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from comments.models import Comment, CommentVote
from posts.models.post import Post


@api(require_auth=True)
@require_http_methods(["GET"])
def api_list_post_comments(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if not post.can_view(request.me):
        raise Http404()

    comments = Comment.visible_objects().filter(post=post)

    return {
        "comments": [comment.to_dict() for comment in comments]
    }


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def toggle_comment_vote(request, comment_id):
    comment = get_object_or_404(Comment.objects.select_related("author", "post"), id=comment_id)

    if not comment.post.can_view(request.me):
        raise Http404()

    if request.method == "POST":
        CommentVote.upvote(user=request.me, comment=comment, request=request)
    elif request.method == "DELETE":
        CommentVote.retract_vote(request=request, user=request.me, comment=comment)

    vote = CommentVote.objects.filter(user=request.me, comment=comment).first()
    comment.refresh_from_db(fields=["upvotes"])

    return {
        "comment": {"upvotes": comment.upvotes},
        "is_voted": vote is not None,
        "upvoted_timestamp": int(vote.created_at.timestamp() * 1000) if vote else 0,
    }
