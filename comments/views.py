import logging
from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from auth.helpers import auth_required
from club.exceptions import AccessDenied, RateLimitException
from comments.forms import CommentForm, ReplyForm, BattleCommentForm
from comments.models import Comment, CommentVote
from common.request import parse_ip_address, parse_useragent, ajax_request
from posts.models.linked import LinkedPost
from posts.models.post import Post
from posts.models.views import PostView
from search.models import SearchIndex

log = logging.getLogger(__name__)


@auth_required
def create_comment(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if not post.is_commentable and not request.me.is_moderator:
        raise AccessDenied(title="Комментарии к этому посту закрыты")

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
                    message="Подождите немного, вы достигли нашего лимита на комментарии в день. "
                            "Можете написать нам в саппорт, пожаловаться об этом."
                )

            comment = form.save(commit=False)
            comment.post = post
            if not comment.author:
                comment.author = request.me

            comment.ipaddress = parse_ip_address(request)
            comment.useragent = parse_useragent(request)
            comment.save()

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

            # return redirect("show_comment", post.slug, comment.id)
            return redirect(
                reverse("show_post", kwargs={"post_type": post.type,
                                             "post_slug": post.slug}) + f"?comment_order={comment_order}#comment-{comment.id}"
            )
        else:
            log.error(f"Comment form error: {form.errors}")
            return render(request, "error.html", {
                "title": "Какая-то ошибка при публикации комментария 🤷‍♂️",
                "message": f"Мы уже получили оповещение и скоро пофиксим. "
                           f"Ваш коммент мы сохранили чтобы вы могли скопировать его и запостить еще раз:",
                "data": form.cleaned_data.get("text")
            })

    raise Http404()


def show_comment(request, post_slug, comment_id):
    post = get_object_or_404(Post, slug=post_slug)
    return redirect(
        reverse("show_post", kwargs={"post_type": post.type, "post_slug": post.slug}) + f"#comment-{comment_id}"
    )


@auth_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if not request.me.is_moderator:
        if comment.author != request.me:
            raise AccessDenied()

        if not comment.is_editable:
            raise AccessDenied(
                title="Время вышло",
                message="Комментарий можно редактировать только в первые 3 часа после создания"
            )

        if not comment.post.is_visible or not comment.post.is_commentable:
            raise AccessDenied(title="Комментарии к этому посту закрыты")

    post = comment.post

    if request.method == "POST":
        form = CommentForm(request.POST, instance=comment)
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
        form = CommentForm(instance=comment)

    return render(request, "comments/edit.html", {
        "comment": comment,
        "post": post,
        "form": form
    })


@auth_required
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
        if comment.deleted_by == request.me or request.me.is_moderator:
            comment.undelete()
            PostView.increment_unread_comments(comment)
        else:
            raise AccessDenied(
                title="Нельзя!",
                message="Только тот, кто удалил комментарий, может его восстановить"
            )

    Comment.update_post_counters(comment.post)

    return redirect("show_comment", comment.post.slug, comment.id)


@auth_required
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


@auth_required
@ajax_request
def upvote_comment(request, comment_id):
    if request.method != "POST":
        raise Http404()

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
        "upvoted_timestamp": int(post_vote.created_at.timestamp() * 1000)
    }


@auth_required
@ajax_request
def retract_comment_vote(request, comment_id):
    if request.method != "POST":
        raise Http404()

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
