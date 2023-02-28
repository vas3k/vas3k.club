from django.http import HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from comments.forms import CommentForm, ReplyForm, BattleCommentForm
from comments.models import Comment
from posts.models.post import Post
from bookmarks.models import PostBookmark
from posts.models.subscriptions import PostSubscription
from posts.models.votes import PostVote
from tags.models import Tag, UserTag
from users.models.mute import Muted
from users.models.notes import UserNote

POSSIBLE_COMMENT_ORDERS = {"created_at", "-created_at", "-upvotes"}


def render_post(request, post, context=None):
    # render "raw" newsletters
    if post.type == Post.TYPE_WEEKLY_DIGEST:
        return HttpResponse(post.html)

    # select votes and comments
    if request.me:
        comments = Comment.objects_for_user(request.me).filter(post=post).all()  # do not add more joins here! it slows down a lot!
        is_bookmark = PostBookmark.objects.filter(post=post, user=request.me).exists()
        is_voted = PostVote.objects.filter(post=post, user=request.me).exists()
        upvoted_at = int(PostVote.objects.filter(post=post, user=request.me).first().created_at.timestamp() * 1000) if is_voted else None
        subscription = PostSubscription.get(request.me, post)
        muted_user_ids = list(Muted.objects.filter(user_from=request.me).values_list("user_to_id", flat=True).all())
        user_notes = dict(UserNote.objects.filter(user_from=request.me).values_list("user_to", "text").all()[:100])
        collectible_tag = Tag.objects.filter(code=post.collectible_tag_code).first() if post.collectible_tag_code else None
        is_collectible_tag_collected = UserTag.objects.filter(tag=collectible_tag, user=request.me).exists() if collectible_tag else False
    else:
        comments = Comment.visible_objects(show_deleted=True).filter(post=post).all()
        is_voted = False
        is_bookmark = False
        upvoted_at = None
        subscription = None
        muted_user_ids = []
        user_notes = {}
        collectible_tag = None
        is_collectible_tag_collected = False

    # order comments
    comment_order = request.GET.get("comment_order") or "-upvotes"
    if comment_order in POSSIBLE_COMMENT_ORDERS:
        comments = comments.order_by(comment_order, "created_at")  # additionally sort by time to preserve an order

    # hide deleted comments for battle (visual junk)
    if post.type == Post.TYPE_BATTLE:
        comments = comments.filter(is_deleted=False)

    comment_form = CommentForm(initial={'text': post.comment_template}) if post.comment_template else CommentForm()
    context = {
        **(context or {}),
        "post": post,
        "comments": comments,
        "comment_form": comment_form,
        "comment_order": comment_order,
        "reply_form": ReplyForm(),
        "is_bookmark": is_bookmark,
        "is_voted": is_voted,
        "upvoted_at": upvoted_at,
        "subscription": subscription,
        "muted_user_ids": muted_user_ids,
        "user_notes": user_notes,
        "collectible_tag": collectible_tag,
        "is_collectible_tag_collected": is_collectible_tag_collected,
    }

    # FIXME: too much hardcoded stuff here. implement a proper type->form mapping in future
    if post.type == Post.TYPE_BATTLE:
        context["comment_form"] = BattleCommentForm()

    try:
        return render(request, f"posts/show/{post.type}.html", context)
    except TemplateDoesNotExist:
        return render(request, "posts/show/post.html", context)
