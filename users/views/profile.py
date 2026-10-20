from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render

from authn.decorators.auth import require_auth
from authn.helpers import check_user_permissions, is_safe_url
from badges.models import UserBadge
from comments.models import Comment
from common.pagination import paginate
from authn.decorators.api import api
from posts.models.post import Post
from search.models import SearchIndex
from users.models.achievements import UserAchievement
from users.models.mute import UserMuted
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
        if is_safe_url(goto):
            return redirect(goto)

        # moderation status check for new-joiners
        access_denied = check_user_permissions(request)
        if access_denied:
            return access_denied

    if not user.can_view(request.me):
        return render(request, "auth/private_profile.html")

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
    projects = Post.visible_objects().filter(author=user, type=Post.TYPE_PROJECT).exclude(
        moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED],
    )
    badges = UserBadge.user_badges_grouped(user=user)
    achievements = UserAchievement.objects.filter(user=user).select_related("achievement")
    if request.me and (request.me.is_curator or request.me.is_moderator):
        visible_posts = Q(visibility=Post.VISIBILITY_EVERYWHERE)
        visible_posts |= Q(visibility=Post.VISIBILITY_LINK_ONLY, moderation_status=Post.MODERATION_PENDING)
        visible_posts |= Q(visibility=Post.VISIBILITY_LINK_ONLY, author=request.me)
        visible_posts |= Q(moderation_status=Post.MODERATION_REJECTED)
        posts = Post.objects.filter(visible_posts)
    else:
        posts = Post.objects_for_user(request.me).exclude(
            moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED],
        )

        if request.me:
            own_moderation_posts = Post.objects.filter(
                author=request.me,
                moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED],
                deleted_at__isnull=True,
            ).exclude(moderation_status=Post.MODERATION_PENDING, visibility=Post.VISIBILITY_DRAFT)
            posts = posts | own_moderation_posts

    posts = posts.filter(Q(author=user) | Q(coauthors__contains=[user.slug])).exclude(
        type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST],
    ).filter(deleted_at__isnull=True).select_related("author", "room", "moderation_user").order_by("-published_at")

    drafts = []
    if request.me and (request.me.id == user.id or request.me.is_curator or request.me.is_moderator):
        drafts = Post.objects.filter(
            author=user, visibility=Post.VISIBILITY_DRAFT, deleted_at__isnull=True,
        ).exclude(moderation_status=Post.MODERATION_REJECTED).select_related("author", "room")[:100]

    if request.me:
        comments = Comment.visible_objects()\
            .filter(author=user)\
            .exclude(post__visibility=Post.VISIBILITY_DRAFT)\
            .order_by("-created_at")\
            .select_related("post")
        muted = UserMuted.objects.filter(user_from=request.me, user_to=user).first()
        note = UserNote.objects.filter(user_from=request.me, user_to=user).first()
    else:
        comments = None
        muted = None
        note = None

    moderator_notes = []
    if request.me and (request.me.is_moderator or request.me.is_curator):
        moderator_notes = UserNote.objects.filter(user_to=user)\
            .exclude(user_from=request.me)\
            .select_related("user_from")\
            .all()

    return render(request, "users/profile.html", {
        "user": user,
        "intro": intro,
        "drafts": drafts,
        "projects": projects,
        "badges": badges,
        "tags": tags,
        "active_tags": active_tags,
        "collectible_tags": collectible_tags,
        "achievements": [ua.achievement for ua in achievements],
        "comments": comments[:3] if comments else [],
        "comments_total": Comment.count_user_comments(user) if comments is not None else 0,
        "posts": posts[:15],
        "posts_total": posts.count(),
        "similarity": similarity,
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
        .filter(author=user)\
        .exclude(post__visibility=Post.VISIBILITY_DRAFT)\
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

    if request.me and (request.me.is_curator or request.me.is_moderator):
        visible_posts = Q(visibility=Post.VISIBILITY_EVERYWHERE)
        visible_posts |= Q(visibility=Post.VISIBILITY_LINK_ONLY, moderation_status=Post.MODERATION_PENDING)
        visible_posts |= Q(visibility=Post.VISIBILITY_LINK_ONLY, author=request.me)
        visible_posts |= Q(moderation_status=Post.MODERATION_REJECTED)
        posts = Post.objects.filter(visible_posts)
    else:
        posts = Post.objects_for_user(request.me).exclude(
            moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED],
        )
        if request.me:
            own_moderation_posts = Post.objects.filter(
                author=request.me,
                moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED],
                deleted_at__isnull=True,
            ).exclude(moderation_status=Post.MODERATION_PENDING, visibility=Post.VISIBILITY_DRAFT)
            posts = posts | own_moderation_posts
    posts = posts.filter(Q(author=user) | Q(coauthors__contains=[user.slug])).exclude(
        type__in=[Post.TYPE_INTRO, Post.TYPE_WEEKLY_DIGEST],
    ).filter(deleted_at__isnull=True).select_related("author", "room", "moderation_user").order_by("-published_at")
    posts = posts.exclude(
        Q(type=Post.TYPE_PROJECT) & ~Q(moderation_status__in=[Post.MODERATION_PENDING, Post.MODERATION_REJECTED])
    )

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
