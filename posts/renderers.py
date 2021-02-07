from django.http import HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from comments.forms import CommentForm, ReplyForm, BattleCommentForm
from comments.models import Comment
from posts.models.post import Post
from bookmarks.models import PostBookmark
from posts.models.subscriptions import PostSubscription
from posts.models.votes import PostVote

POSSIBLE_COMMENT_ORDERS = {"created_at", "-created_at", "-upvotes"}


def render_post(request, post, context=None):
    # render "raw" newsletters
    if post.type == Post.TYPE_WEEKLY_DIGEST:
        return HttpResponse(post.html)

    # select votes and comments
    if request.me:
        comments = Comment.objects_for_user(request.me).filter(post=post).all()
        is_bookmark = PostBookmark.objects.filter(post=post, user=request.me).exists()
        is_voted = PostVote.objects.filter(post=post, user=request.me).exists()
        upvoted_at = int(PostVote.objects.filter(post=post, user=request.me).first().created_at.timestamp() * 1000) if is_voted else None
        subscription = PostSubscription.get(request.me, post)
    else:
        comments = Comment.visible_objects(show_deleted=True).filter(post=post).all()
        is_voted = False
        is_bookmark = False
        upvoted_at = None
        subscription = None

    # order comments
    comment_order = request.GET.get("comment_order") or "-upvotes"
    if comment_order in POSSIBLE_COMMENT_ORDERS:
        comments = comments.order_by(comment_order, "created_at")  # additionally sort by time to preserve an order

    # hide deleted comments for battle (visual junk)
    if post.type == Post.TYPE_BATTLE:
        comments = comments.filter(is_deleted=False)

    context = {
        **(context or {}),
        "post": post,
        "comments": comments,
        "comment_form": CommentForm(),
        "comment_order": comment_order,
        "reply_form": ReplyForm(),
        "is_bookmark": is_bookmark,
        "is_voted": is_voted,
        "upvoted_at": upvoted_at,
        "subscription": subscription,
    }

    # TODO: make a proper mapping here in future
    if post.type == Post.TYPE_BATTLE:
        context["comment_form"] = BattleCommentForm()

    try:
        return render(request, f"posts/show/{post.type}.html", context)
    except TemplateDoesNotExist:
        return render(request, "posts/show/post.html", context)
