from datetime import datetime, timezone

from django.conf import settings
from django.shortcuts import get_object_or_404, render
from django_q.tasks import async_task

from authn.decorators.auth import require_auth
from badges.models import Badge, UserBadge
from club.exceptions import BadRequest
from comments.models import Comment
from notifications.email.badges import send_new_badge_email
from notifications.telegram.badges import send_new_badge_message
from posts.models.post import Post


@require_auth
def create_badge_for_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if post.deleted_at:
        raise BadRequest(
            title="😵 Пост удалён",
            message="Нельзя давать награды за удалённые посты"
        )

    if request.method != "POST":
        if request.me.membership_days_left() < settings.MIN_DAYS_TO_GIVE_BADGES:
            return render(request, "badges/messages/insufficient_funds.html")

        if post.type == Post.TYPE_INTRO:
            badges = Badge.badges_for_intro()
        else:
            badges = Badge.badges_for_post_or_comment()

        return render(request, "badges/create.html", {
            "post": post,
            "badges": badges,
        })

    badge_code = request.POST.get("badge_code")
    badge = Badge.objects.filter(code=badge_code).first()
    if not badge or not badge.is_visible:
        raise BadRequest(
            title="🙅‍♀️ Бейджик недоступен",
            message="Данную награду пока нельзя выдавать"
        )

    note = (request.POST.get("note") or "")[:1000]
    user_badge = UserBadge.create_user_badge(
        badge=badge,
        from_user=request.me,
        to_user=post.author,
        post=post,
        note=note,
    )

    # send notifications
    async_task(send_new_badge_email, user_badge)
    async_task(send_new_badge_message, user_badge)

    # bump post on home page by updating its last_activity_at
    Post.objects.filter(id=post.id).update(last_activity_at=datetime.now(timezone.utc))

    # show insufficient funds warning if < 3 months
    membership_days_remaining = request.me.membership_days_left() - user_badge.badge.price_days
    show_funds_warning = membership_days_remaining < settings.MIN_DAYS_TO_GIVE_BADGES * 3

    return render(request, "badges/messages/success.html", {
        "user_badge": user_badge,
        "show_funds_warning": show_funds_warning,
        "membership_days_remaining": membership_days_remaining,
    })


@require_auth
def create_badge_for_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.is_deleted:
        raise BadRequest(
            title="😵 Комментарий удалён",
            message="Нельзя выдавать награды за удалённые комменты"
        )
    if comment.author.deleted_at:
        raise BadRequest(
            title="😵 Пользователь удалился",
            message="Нельзя выдавать награды удалённым юзерам"
        )
    if comment.author == request.me:
        raise BadRequest(
            title="😵 Это же ты",
            message="Нельзя выдавать награды самому себе"
        )
    if request.method != "POST":
        if request.me.membership_days_left() < settings.MIN_DAYS_TO_GIVE_BADGES:
            return render(request, "badges/messages/insufficient_funds.html")

        badges = Badge.badges_for_post_or_comment()

        return render(request, "badges/create.html", {
            "comment": comment,
            "badges": badges,
        })

    badge_code = request.POST.get("badge_code")
    badge = Badge.objects.filter(code=badge_code).first()
    if not badge or not badge.is_visible:
        raise BadRequest(
            title="🙅‍♀️ Бейджик недоступен",
            message="Данную награду пока нельзя выдавать"
        )

    note = (request.POST.get("note") or "")[:1000]
    user_badge = UserBadge.create_user_badge(
        badge=badge,
        from_user=request.me,
        to_user=comment.author,
        comment=comment,
        note=note,
    )

    # send notifications
    async_task(send_new_badge_email, user_badge)
    async_task(send_new_badge_message, user_badge)

    # bump post on home page by updating its last_activity_at
    Post.objects.filter(id=comment.post_id).update(last_activity_at=datetime.now(timezone.utc))

    # show insufficient funds warning if < 3 months
    membership_days_remaining = request.me.membership_days_left() - user_badge.badge.price_days
    show_funds_warning = membership_days_remaining < settings.MIN_DAYS_TO_GIVE_BADGES * 3

    return render(request, "badges/messages/success.html", {
        "user_badge": user_badge,
        "show_funds_warning": show_funds_warning,
        "membership_days_remaining": membership_days_remaining,
    })
