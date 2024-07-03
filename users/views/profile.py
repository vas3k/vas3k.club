from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render

from authn.decorators.auth import require_auth
from authn.helpers import check_user_permissions
from badges.models import UserBadge
from comments.models import Comment
from common.pagination import paginate
from authn.decorators.api import api
from posts.models.post import Post
from search.models import SearchIndex
from users.models.achievements import UserAchievement
from users.models.friends import Friend
from users.models.mute import Muted
from tags.models import Tag, UserTag
from users.models.notes import UserNote
from users.models.user import User
from users.utils import calculate_similarity


def profile(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("profile", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)

    if request.me and user.id == request.me.id:
        # handle auth redirect
        goto = request.GET.get("goto")
        if goto and goto.startswith(settings.APP_HOST):
            return redirect(goto)

        # moderation status check for new-joiners
        access_denied = check_user_permissions(request)
        if access_denied:
            return access_denied

    if not user.can_view(request.me):
        return render(request, "auth/private_profile.html")

    if user.moderation_status != User.MODERATION_STATUS_APPROVED:
        # hide unverified users (but still show to moderators)
        if not request.me or not request.me.is_moderator:
            raise Http404()

    # select user tags and calculate similarity with me
    tags = Tag.objects.filter(is_visible=True).exclude(group=Tag.GROUP_COLLECTIBLE).all()
    user_tags = UserTag.objects.filter(user=user).select_related("tag").all()
    active_tags = {t.tag_id for t in user_tags if t.tag.group != Tag.GROUP_COLLECTIBLE}
    collectible_tags = [t.tag for t in user_tags if t.tag.group == Tag.GROUP_COLLECTIBLE]
    similarity = {}
    if request.me and user.id != request.me.id:
        my_tags = {t.tag_id for t in UserTag.objects.filter(user=request.me).all()}
        similarity = calculate_similarity(my_tags, active_tags, tags)

    # select other stuff from this user
    intro = Post.get_user_intro(user)
    projects = Post.objects.filter(author=user, type=Post.TYPE_PROJECT, is_visible=True).all()
    badges = UserBadge.user_badges_grouped(user=user)
    achievements = UserAchievement.objects.filter(user=user).select_related("achievement")
    posts = Post.objects_for_user(request.me).filter(is_visible=True)\
        .filter(Q(author=user) | Q(coauthors__contains=[user.slug]))\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_PROJECT, Post.TYPE_WEEKLY_DIGEST])\
        .order_by("-published_at")

    if request.me:
        comments = Comment.visible_objects()\
            .filter(author=user, post__is_visible=True)\
            .order_by("-created_at")\
            .select_related("post")
        friend = Friend.objects.filter(user_from=request.me, user_to=user).first()
        muted = Muted.objects.filter(user_from=request.me, user_to=user).first()
        note = UserNote.objects.filter(user_from=request.me, user_to=user).first()
    else:
        comments = None
        friend = None
        muted = None
        note = None

    moderator_notes = []
    if request.me and request.me.is_moderator:
        moderator_notes = UserNote.objects.filter(user_to=user)\
            .exclude(user_from=request.me)\
            .select_related("user_from")\
            .all()

    return render(request, "users/profile.html", {
        "user": user,
        "intro": intro,
        "projects": projects,
        "badges": badges,
        "tags": tags,
        "active_tags": active_tags,
        "collectible_tags": collectible_tags,
        "achievements": [ua.achievement for ua in achievements],
        "comments": comments[:3] if comments else [],
        "comments_total": comments.count() if comments else 0,
        "posts": posts[:15],
        "posts_total": posts.count() if posts else 0,
        "similarity": similarity,
        "friend": friend,
        "muted": muted,
        "note": note,
        "moderator_notes": moderator_notes,
    })


@require_auth
def profile_comments(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("profile_comments", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)

    comments = Comment.visible_objects()\
        .filter(author=user, post__is_visible=True)\
        .order_by("-created_at")\
        .select_related("post")

    return render(request, "users/profile/comments.html", {
        "user": user,
        "comments": paginate(request, comments, settings.PROFILE_COMMENTS_PAGE_SIZE),
    })


def profile_posts(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("profile_posts", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)

    if not user.can_view(request.me):
        return render(request, "auth/private_profile.html")

    posts = Post.objects_for_user(request.me) \
        .filter(is_visible=True) \
        .filter(Q(author=user) | Q(coauthors__contains=[user.slug])) \
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_PROJECT, Post.TYPE_WEEKLY_DIGEST]) \
        .order_by("-published_at")

    return render(request, "users/profile/posts.html", {
        "user": user,
        "posts": paginate(request, posts, settings.PROFILE_POSTS_PAGE_SIZE),
    })


def profile_badges(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("profile_badges", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)

    if not user.can_view(request.me):
        return render(request, "auth/private_profile.html")

    badges = UserBadge.user_badges(user)

    return render(request, "users/profile/badges.html", {
        "user": user,
        "badges": paginate(request, badges, settings.PROFILE_BADGES_PAGE_SIZE),
    })


@api(require_auth=True)
def toggle_tag(request, tag_code):
    if request.method != "POST":
        raise Http404()

    tag = get_object_or_404(Tag, code=tag_code)

    user_tag, is_created = UserTag.objects.get_or_create(
        user=request.me, tag=tag, defaults=dict(name=tag.name)
    )

    if not is_created:
        user_tag.delete()

    SearchIndex.update_user_tags(request.me)

    return {
        "status": "created" if is_created else "deleted",
        "tag": {"code": tag.code, "name": tag.name, "color": tag.color},
    }
