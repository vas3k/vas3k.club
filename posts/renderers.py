from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template import TemplateDoesNotExist

from comments.forms import CommentForm, ReplyForm, BattleCommentForm
from comments.models import Comment, CommentVote
from comments.rate_limits import is_comment_rate_limit_exceeded
from common.markdown.markdown import markdown_text
from posts.models.post import Post
from bookmarks.models import PostBookmark
from posts.models.subscriptions import PostSubscription
from posts.models.votes import PostVote
from tags.models import Tag, UserTag
from users.models.mute import UserMuted
from users.models.notes import UserNote

POSSIBLE_COMMENT_ORDERS = {"created_at", "-created_at", "-upvotes"}

COMMENT_DEFERRED_FIELDS = ("ipaddress", "useragent", "url")


def render_post(request, post, context=None):
    if post.type == Post.TYPE_WEEKLY_DIGEST:
        return HttpResponse(post.html)

    comments = Comment.objects \
        .filter(post=post, is_visible=True) \
        .select_related("author") \
        .defer(*COMMENT_DEFERRED_FIELDS) \
        .order_by("created_at")

    if request.me:
        is_bookmark = PostBookmark.objects.filter(post=post, user=request.me).exists()
        upvoted_at_dt = PostVote.objects.filter(post=post, user=request.me).values_list("created_at", flat=True).first()
        upvoted_at = int(upvoted_at_dt.timestamp() * 1000) if upvoted_at_dt else None
        subscription = PostSubscription.get(request.me, post)
        muted_user_ids = list(UserMuted.objects.filter(user_from=request.me).values_list("user_to_id", flat=True))
        user_notes = dict(UserNote.objects.filter(user_from=request.me).values_list("user_to", "text")[:100])
        if post.collectible_tag_code:
            collectible_tag = Tag.objects.filter(code=post.collectible_tag_code).first()
            is_collectible_tag_collected = UserTag.objects.filter(
                tag=collectible_tag, user=request.me
            ).exists() if collectible_tag else False
        else:
            collectible_tag = None
            is_collectible_tag_collected = False
        is_comment_rate_exceeded = is_comment_rate_limit_exceeded(post, request.me)
    else:
        is_bookmark = False
        upvoted_at = None
        subscription = None
        muted_user_ids = []
        user_notes = {}
        collectible_tag = None
        is_collectible_tag_collected = False
        is_comment_rate_exceeded = False

    comment_order = request.GET.get("comment_order") or "-upvotes"
    if comment_order in POSSIBLE_COMMENT_ORDERS:
        comments = comments.order_by(comment_order, "created_at")

    # battle hides deleted comments to keep the voting UI clean
    if post.type == Post.TYPE_BATTLE:
        comments = comments.filter(is_deleted=False)

    comments = list(comments)
    _warm_comment_html_cache(comments)

    # avoid N lazy post lookups: all comments share the same post
    for comment in comments:
        comment.post = post

    # fetch votes in one query instead of correlated subquery per comment
    if request.me:
        comment_ids = [c.id for c in comments]
        vote_map = dict(
            CommentVote.objects.filter(
                comment_id__in=comment_ids,
                user=request.me,
            ).values_list("comment_id", "created_at")
        )
        for comment in comments:
            ts = vote_map.get(comment.id)
            comment.upvoted_at = int(ts.timestamp() * 1000) if ts else None
    else:
        for comment in comments:
            comment.upvoted_at = None

    comment_form = CommentForm(initial={'text': post.comment_template}) if post.comment_template else CommentForm()
    context = {
        **(context or {}),
        "post": post,
        "comments": comments,
        "comment_form": comment_form,
        "comment_order": comment_order,
        "reply_form": ReplyForm(),
        "is_bookmark": is_bookmark,
        "upvoted_at": upvoted_at,
        "subscription": subscription,
        "muted_user_ids": muted_user_ids,
        "user_notes": user_notes,
        "collectible_tag": collectible_tag,
        "is_collectible_tag_collected": is_collectible_tag_collected,
        "is_comment_rate_exceeded": is_comment_rate_exceeded,
    }

    # FIXME: too much hardcoded stuff here. implement a proper type->form mapping in future
    if post.type == Post.TYPE_BATTLE:
        context["comment_form"] = BattleCommentForm()

    try:
        return render(request, f"posts/show/{post.type}.html", context)
    except TemplateDoesNotExist:
        return render(request, "posts/show/post.html", context)


def _warm_comment_html_cache(comments):
    if settings.DEBUG:
        return

    to_update = []
    now = datetime.utcnow()
    for comment in comments:
        if comment.is_deleted or comment.html:
            continue
        comment.html = markdown_text(comment.text, uniq_id=comment.id)
        comment.updated_at = now
        to_update.append(comment)

    if to_update:
        Comment.objects.bulk_update(to_update, ["html", "updated_at"])
