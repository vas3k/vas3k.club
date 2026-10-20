from functools import wraps

from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from authn.decorators.api import api
from authn.decorators.auth import require_auth
from authn.helpers import check_user_permissions, is_safe_url
from badges.models import UserBadge
from comments.models import Comment
from common.pagination import paginate
from posts.models.post import Post
from rooms.models import RoomSubscription
from search.models import SearchIndex
from tags.models import Tag, UserTag
from users.models.achievements import UserAchievement
from users.models.mute import UserMuted
from users.models.notes import UserNote
from users.models.user import User
from users.utils import calculate_similarity


def profile_page(view):
    @wraps(view)
    def wrapper(request, user_slug):
        if user_slug == "me" and request.me:
            return redirect(view.__name__, request.me.slug, permanent=False)

        user = get_object_or_404(User, slug=user_slug)

        if not user.can_view(request.me):
            return render(request, "auth/private_profile.html")

        return view(request, user)

    return wrapper


def visible_profile_posts(user, viewer):
    moderation_statuses = [Post.MODERATION_PENDING, Post.MODERATION_REJECTED]

    if viewer and (viewer.is_curator or viewer.is_moderator):
        visibility = Q(visibility=Post.VISIBILITY_EVERYWHERE)
        visibility |= Q(visibility=Post.VISIBILITY_LINK_ONLY, moderation_status=Post.MODERATION_PENDING)
        visibility |= Q(visibility=Post.VISIBILITY_LINK_ONLY, author=viewer)
        visibility |= Q(moderation_status=Post.MODERATION_REJECTED)
        posts = Post.objects.filter(visibility)
    else:
        posts = Post.objects_for_user(viewer).exclude(moderation_status__in=moderation_statuses)

        if viewer:
            own_moderation_posts = Post.objects.filter(
                author=viewer, moderation_status__in=moderation_statuses,
            ).exclude(moderation_status=Post.MODERATION_PENDING, visibility=Post.VISIBILITY_DRAFT)
            posts = posts | own_moderation_posts

    return posts.filter(
        Q(author=user) | Q(coauthors__contains=[user.slug]), deleted_at__isnull=True,
    ).exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST]).select_related("author", "room")


@profile_page
def profile(request, user):
    viewer = request.me
    is_owner = bool(viewer and viewer.id == user.id)
    is_staff = bool(viewer and (viewer.is_curator or viewer.is_moderator))

    if is_owner:
        goto = request.GET.get("goto")

        if is_safe_url(goto):
            return redirect(goto)

        access_denied = check_user_permissions(request)

        if access_denied:
            return access_denied

    tags = Tag.objects.filter(is_visible=True).exclude(group=Tag.GROUP_COLLECTIBLE)
    user_tags = list(UserTag.objects.filter(user=user).select_related("tag"))
    active_tags = {tag.tag_id for tag in user_tags if tag.tag.group != Tag.GROUP_COLLECTIBLE}
    posts = visible_profile_posts(user, viewer).order_by("-published_at")
    projects = visible_profile_posts(user, viewer).filter(
        author=user, type=Post.TYPE_PROJECT, visibility=Post.VISIBILITY_EVERYWHERE,
    ).exclude(moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED]).order_by("-created_at")

    context = {
        "user": user,
        "intro": Post.get_user_intro(user),
        "projects": projects,
        "badges": UserBadge.user_badges_grouped(user=user),
        "achievements": [
            item.achievement for item in UserAchievement.objects.filter(user=user).select_related("achievement")
        ],
        "tags": tags,
        "active_tags": active_tags,
        "collectible_tags": [tag.tag for tag in user_tags if tag.tag.group == Tag.GROUP_COLLECTIBLE],
        "posts": posts[:15],
        "posts_total": posts.count(),
        "drafts": [],
        "comments": [],
        "comments_total": 0,
        "room_subscriptions": RoomSubscription.objects.none(),
        "similarity": {},
        "muted": None,
        "note": None,
        "moderator_notes": [],
    }

    if viewer:
        comments = Comment.visible_objects().filter(author=user).exclude(
            post__visibility=Post.VISIBILITY_DRAFT,
        ).select_related("post").order_by("-created_at")
        context.update({
            "comments": comments[:3],
            "comments_total": comments.count(),
            "muted": UserMuted.objects.filter(user_from=viewer, user_to=user).first(),
            "note": UserNote.objects.filter(user_from=viewer, user_to=user).first(),
            "room_subscriptions": RoomSubscription.objects.filter(
                Q(is_chat_member=True) | Q(is_notified=True), user=user, room__is_visible=True,
            ).select_related("room").order_by("-room__chat_member_count", "room_id"),
        })

        if not is_owner:
            my_tags = set(UserTag.objects.filter(user=viewer).values_list("tag_id", flat=True))
            context["similarity"] = calculate_similarity(my_tags, active_tags, tags)

        if is_owner or is_staff:
            context["drafts"] = Post.objects.filter(
                author=user, visibility=Post.VISIBILITY_DRAFT, deleted_at__isnull=True,
            ).exclude(moderation_status=Post.MODERATION_REJECTED).select_related("author", "room")[:100]

        if is_staff:
            context["moderator_notes"] = UserNote.objects.filter(user_to=user).exclude(
                user_from=viewer,
            ).select_related("user_from")

    return render(request, "users/profile.html", context)


@require_auth
@profile_page
def profile_comments(request, user):
    comments = Comment.visible_objects().filter(author=user).exclude(
        post__visibility=Post.VISIBILITY_DRAFT,
    ).select_related("post").order_by("-created_at")

    return render(request, "users/profile/comments.html", {
        "user": user,
        "comments": paginate(request, comments, settings.PROFILE_COMMENTS_PAGE_SIZE),
    })


@profile_page
def profile_posts(request, user):
    posts = visible_profile_posts(user, request.me).exclude(
        Q(type=Post.TYPE_PROJECT) & ~Q(moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED]),
    ).order_by("-published_at")

    return render(request, "users/profile/posts.html", {
        "user": user,
        "posts": paginate(request, posts, settings.PROFILE_POSTS_PAGE_SIZE),
    })


@profile_page
def profile_badges(request, user):
    return render(request, "users/profile/badges.html", {
        "user": user,
        "badges": paginate(request, UserBadge.user_badges(user), settings.PROFILE_BADGES_PAGE_SIZE),
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
