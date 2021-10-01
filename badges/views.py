from django.shortcuts import get_object_or_404, render

from auth.helpers import auth_required
from badges.models import Badge, UserBadge
from club.exceptions import BadRequest
from comments.models import Comment
from posts.models.post import Post


@auth_required
def give_badge_for_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if post.deleted_at:
        raise BadRequest(title="Пост удалён", message="Нельзя давать бейджики за удалённые посты")

    if request.method == "POST":
        badge_code = request.POST.get("badge_code")
        badge = get_object_or_404(Badge, code=badge_code)
        if not badge.is_visible:
            raise BadRequest(title="Бейджик скрыт", message="Пока его нельзя выдавать")

        user_badge = UserBadge.create_user_badge(
            badge=badge,
            from_user=request.me,
            to_user=post.author,
            post=post,
        )

        return render(request, "badges/success.html", {
            "user_badge": user_badge,
        })
    else:
        return render(request, "badges/badge_for_post.html", {
            "post": post,
            "badges": Badge.visible_objects().all(),
        })


@auth_required
def give_badge_for_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.is_deleted:
        raise BadRequest(title="Коммент удалён", message="Нельзя давать бейджики за удалённые комменты")

    if request.method == "POST":
        badge_code = request.POST.get("badge_code")
        badge = get_object_or_404(Badge, code=badge_code)
        if not badge.is_visible:
            raise BadRequest(title="Бейджик скрыт", message="Пока его нельзя выдавать")

        user_badge = UserBadge.create_user_badge(
            badge=badge,
            from_user=request.me,
            to_user=comment.author,
            post=comment.post,
            comment=comment,
        )

        return render(request, "badges/success.html", {
            "user_badge": user_badge,
        })
    else:
        return render(request, "badges/badge_for_comment.html", {
            "comment": comment,
            "badges": Badge.visible_objects().all(),
        })
