import logging

from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied, RateLimitException
from comments.forms import CommentForm, ReplyForm, BattleCommentForm, edit_form_class_for_comment
from comments.models import Comment, CommentVote
from common.request import parse_ip_address, parse_useragent
from authn.decorators.api import api
from posts.models.linked import LinkedPost
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from posts.models.views import PostView
from search.models import SearchIndex

log = logging.getLogger(__name__)


@require_auth
def create_comment(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if not post.is_commentable and not request.me.is_moderator:
        raise AccessDenied(
            title="Комментарии к этому посту закрыты",
            data={"saved_text": request.POST.get("text")},
        )

    if request.POST.get("reply_to_id"):
        ProperCommentForm = ReplyForm
    elif post.type == Post.TYPE_BATTLE:
        ProperCommentForm = BattleCommentForm
    else:
        ProperCommentForm = CommentForm

    comment_order = request.POST.get("post_comment_order", "created_at")

    if request.method == "POST":
        form = ProperCommentForm(request.POST)
        if form.is_valid():
            is_ok = Comment.check_rate_limits(request.me)
            if not is_ok:
                raise RateLimitException(
                    title="🙅‍♂️ Вы комментируете слишком часто",
                    message="Подождите немного, вы достигли своего лимита на комментарии в день.",
                    data={"saved_text": request.POST.get("text")},
                )

            comment = form.save(commit=False)
            comment.post = post
            if not comment.author:
                comment.author = request.me

            comment.ipaddress = parse_ip_address(request)
            comment.useragent = parse_useragent(request)
            comment.save()

            # subscribe to top level comments
            if form.cleaned_data.get("subscribe_to_post"):
                PostSubscription.subscribe(
                    user=request.me,
                    post=post,
                    type=PostSubscription.TYPE_ALL_COMMENTS if post.author_id == request.me.id
                    else PostSubscription.TYPE_TOP_LEVEL_ONLY
                )

            # update the shitload of counters :)
            request.me.update_last_activity()
            Comment.update_post_counters(post)
            PostView.increment_unread_comments(comment)
            PostView.register_view(
                request=request,
                user=request.me,
                post=post,
            )
            SearchIndex.update_comment_index(comment)
            LinkedPost.create_links_from_text(post, comment.text)
            return redirect(
                reverse("show_post", kwargs={
                    "post_type": post.type,
                    "post_slug": post.slug
                }) + f"?comment_order={comment_order}#comment-{comment.id}"
            )
        else:
            log.error(f"Comment form error: {form.errors}")
            return render(request, "error.html", {
                "title": "Какая-то ошибка при публикации комментария 🤷‍♂️",
                "message": f"Мы уже получили оповещение и скоро пофиксим. "
                           f"Ваш коммент мы сохранили чтобы вы могли скопировать его и запостить еще раз:",
                "data": {"saved_text": form.cleaned_data.get("text")}
            }, status=500)

    raise Http404()


def show_comment(request, post_slug, comment_id):
    post = get_object_or_404(Post, slug=post_slug)
    return redirect(
        reverse("show_post", kwargs={"post_type": post.type, "post_slug": post.slug}) + f"#comment-{comment_id}"
    )


@require_auth
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if not request.me.is_moderator:
        if comment.author != request.me:
            raise AccessDenied()

        if comment.is_deleted:
            raise AccessDenied(
                title="Нельзя редактировать удаленный комментарий",
                message="Сначала тот, кто его удалил, должен его восстановить"
            )

        if not comment.is_editable:
            hours = int(settings.COMMENT_EDITABLE_TIMEDELTA.total_seconds() // 3600)
            raise AccessDenied(
                title="Время вышло",
                message=f"Комментарий можно редактировать только в течение {hours} часов после создания"
            )

        if not comment.post.is_visible or not comment.post.is_commentable:
            raise AccessDenied(title="Комментарии к этому посту закрыты")

    post = comment.post
    FormClass = edit_form_class_for_comment(comment)

    if request.method == "POST":
        form = FormClass(request.POST, instance=comment)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.is_deleted = False
            comment.html = None  # flush cache
            comment.ipaddress = parse_ip_address(request)
            comment.useragent = parse_useragent(request)
            comment.save()

            SearchIndex.update_comment_index(comment)

            return redirect("show_comment", post.slug, comment.id)
    else:
        form = FormClass(instance=comment)

    return render(request, "comments/edit.html", {
        "comment": comment,
        "post": post,
        "form": form
    })


@require_auth
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if not request.me.is_moderator:
        # only comment author, post author or moderator can delete comments
        if comment.author != request.me and request.me != comment.post.author:
            raise AccessDenied(
                title="Нельзя!",
                message="Только автор комментария, поста или модератор может удалить комментарий"
            )

        if not comment.is_deletable_by(request.me):
            raise AccessDenied(
                title="Время вышло",
                message="Комментарий можно удалять только в первые дни после создания. "
                        "Потом только автор или модератор может это сделать."
            )

        if not comment.post.is_visible:
            raise AccessDenied(
                title="Пост скрыт!",
                message="Нельзя удалять комментарии к скрытому посту"
            )

    if not comment.is_deleted:
        # delete comment
        comment.delete(deleted_by=request.me)
        PostView.decrement_unread_comments(comment)
    else:
        # undelete comment
        if comment.deleted_by == request.me.id or request.me.is_moderator:
            comment.undelete()
            PostView.increment_unread_comments(comment)
        else:
            raise AccessDenied(
                title="Нельзя!",
                message="Только тот, кто удалил комментарий, может его восстановить"
            )

    Comment.update_post_counters(comment.post, update_activity=False)

    return redirect("show_comment", comment.post.slug, comment.id)


@require_auth
def delete_comment_thread(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if not request.me.is_moderator:
        # only moderator can delete whole threads
        raise AccessDenied(
            title="Нельзя!",
            message="Только модератор может удалять треды"
        )

    # delete child comments completely
    Comment.objects.filter(Q(reply_to=comment) | Q(reply_to__reply_to=comment)).delete()
    Comment.objects.filter(id=comment_id).delete()

    return redirect("show_post", comment.post.type, comment.post.slug)


@require_auth
def pin_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if not request.me.is_moderator and comment.post.author != request.me:
        raise AccessDenied(
            title="Нельзя!",
            message="Только автор поста или модератор может пинить посты"
        )

    if comment.reply_to:
        raise AccessDenied(
            title="Нельзя!",
            message="Можно пинить только комменты первого уровня"
        )

    comment.is_pinned = not comment.is_pinned  # toggle pin/unpin
    comment.save()

    return redirect("show_comment", comment.post.slug, comment.id)


@api(require_auth=True)
@require_http_methods(["POST"])
def upvote_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    post_vote, is_created = CommentVote.upvote(
        user=request.me,
        comment=comment,
        request=request,
    )

    return {
        "comment": {
            "upvotes": comment.upvotes + (1 if is_created else 0)
        },
        "upvoted_timestamp": int(post_vote.created_at.timestamp() * 1000) if post_vote else 0
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def retract_comment_vote(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    is_retracted = CommentVote.retract_vote(
        request=request,
        user=request.me,
        comment=comment,
    )

    return {
        "success": is_retracted,
        "comment": {
            "upvotes": comment.upvotes - (1 if is_retracted else 0)
        }
    }
