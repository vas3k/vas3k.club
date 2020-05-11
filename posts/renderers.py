from django.http import HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from comments.forms import CommentForm, ReplyForm, BattleCommentForm
from comments.models import Comment
from posts.models import PostVote, Post

POSSIBLE_COMMENT_ORDERS = {"created_at", "-created_at", "-upvotes"}


def render_post(request, post):
    # render "raw" newsletters
    if post.type == Post.TYPE_WEEKLY_DIGEST:
        return HttpResponse(post.html)

    # select votes and comments
    is_voted = False
    if request.me:
        comments = Comment.objects_for_user(request.me).filter(post=post).all()
        is_voted = PostVote.objects.filter(post=post, user=request.me).exists()
    else:
        comments = Comment.visible_objects().filter(post=post).all()

    # order comments
    comment_order = request.GET.get("comment_order") or "-upvotes"
    if comment_order in POSSIBLE_COMMENT_ORDERS:
        comments = comments.order_by(comment_order)

    # hide deleted comments for battle (visual junk)
    if post.type == Post.TYPE_BATTLE:
        comments = comments.filter(is_deleted=False)

    context = {
        "post": post,
        "comments": comments,
        "comment_form": CommentForm(),
        "comment_order": comment_order,
        "reply_form": ReplyForm(),
        "is_voted": is_voted,
    }

    # TODO: make pretty mapping here in future
    if post.type == Post.TYPE_BATTLE:
        context["comment_form"] = BattleCommentForm()

    try:
        return render(request, f"posts/show/{post.type}.html", context)
    except TemplateDoesNotExist:
        return render(request, "posts/show/post.html", context)
