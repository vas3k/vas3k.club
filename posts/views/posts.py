from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from authn.helpers import check_user_permissions
from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied, ContentDuplicated, RateLimitException
from authn.decorators.api import api
from posts.forms.compose import POST_TYPE_MAP, PostTextForm
from posts.models.linked import LinkedPost
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from posts.models.views import PostView
from posts.models.votes import PostVote
from posts.renderers import render_post
from search.models import SearchIndex


def show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    # post_type can be changed by moderator
    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    # drafts are visible only to authors, coauthors and moderators
    if not post.can_view(request.me):
        raise Http404()

    # don't show private posts into public
    if not post.is_public:
        access_denied = check_user_permissions(request, post=post)
        if access_denied:
            return access_denied

    # record a new view
    last_view_at = None
    if request.me:
        request.me.update_last_activity()
        post_view, last_view_at = PostView.register_view(
            request=request,
            user=request.me,
            post=post,
        )
    else:
        PostView.register_anonymous_view(
            request=request,
            post=post,
        )

    # find linked posts and sort them by upvotes
    linked_posts = sorted({
        link.post_to if link.post_to != post else link.post_from
        for link in LinkedPost.links_for_post(post)[:50]
    }, key=lambda p: p.upvotes, reverse=True)

    # force cleanup deleted/hidden posts from linked
    linked_posts = [p for p in linked_posts if p.is_visible]

    return render_post(request, post, {
        "post_last_view_at": last_view_at,
        "linked_posts": linked_posts,
    })


@require_auth
def unpublish_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if not request.me.is_moderator:
        if post.author != request.me:
            raise AccessDenied(title="Только автор или модератор может удалить пост")

        if not post.is_safely_deletable_by_author:
            raise AccessDenied(
                title="Только модератор может полностью удалить этот пост",
                message=f"Так как в нём уже больше {settings.MAX_COMMENTS_FOR_DELETE_VS_CLEAR} комментов "
                        f"и некоторые из них могут быть ценны их авторам и коммьюнити в целом"
            )

    post.unpublish()

    return redirect("show_post", post.type, post.slug)


@require_auth
def clear_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if post.author != request.me and not request.me.is_moderator:
        raise AccessDenied(title="Только автор или модератор может очистить пост")

    post.clear()

    return redirect("show_post", post.type, post.slug)


@require_auth
def delete_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if post.author != request.me:
        raise AccessDenied()

    if post.deleted_at:
        # restore post
        post.undelete()
    else:
        # delete post
        post.delete()

    return redirect("compose")


@api(require_auth=True)
@require_http_methods(["POST"])
def upvote_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    post_vote, is_vote_created = PostVote.upvote(
        user=request.me,
        post=post,
        request=request,
    )

    return {
        "post": {
            "upvotes": post.upvotes + (1 if is_vote_created else 0),
        },
        "upvoted_timestamp": int(post_vote.created_at.timestamp() * 1000) if post_vote else 0
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def retract_post_vote(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    is_retracted = PostVote.retract_vote(
        request=request,
        user=request.me,
        post=post,
    )

    return {
        "success": is_retracted,
        "post": {
            "upvotes": post.upvotes - (1 if is_retracted else 0)
        }
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_post_subscription(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    subscription, is_created = PostSubscription.subscribe(
        user=request.me,
        post=post,
        type=PostSubscription.TYPE_TOP_LEVEL_ONLY,
    )

    if not is_created:
        # already exist? remove it
        PostSubscription.unsubscribe(
            user=request.me,
            post=post,
        )

    return {
        "status": "created" if is_created else "deleted"
    }


@require_auth
def compose(request):
    drafts = Post.objects\
        .filter(is_visible=False, deleted_at__isnull=True)\
        .filter(Q(author=request.me) | Q(coauthors__contains=[request.me.slug]))[:100]

    return render(request, "posts/compose/compose.html", {
        "drafts": drafts
    })


@require_auth
def compose_type(request, post_type):
    if post_type not in dict(Post.TYPES):
        raise Http404()

    return create_or_edit(request, post_type, mode="create")


@require_auth
def edit_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if not post.can_edit(request.me):
        raise AccessDenied()

    return create_or_edit(request, post.type, post=post, mode="edit")


def create_or_edit(request, post_type, post=None, mode="create"):
    FormClass = POST_TYPE_MAP.get(post_type) or PostTextForm

    # show blank form on GET
    if request.method != "POST":
        form = FormClass(instance=post)
        return render(request, f"posts/compose/{post_type}.html", {
            "mode": mode,
            "post_type": post_type,
            "form": form,
        })

    # validate form on POST
    form = FormClass(request.POST, request.FILES, instance=post)
    if form.is_valid():
        if (post and post.type != Post.TYPE_INTRO) and not request.me.is_moderator:
            if Post.check_duplicate(
                user=request.me,
                title=form.cleaned_data["title"],
                ignore_post_id=post.id if post else None
            ):
                raise ContentDuplicated()

            is_ok = Post.check_rate_limits(request.me)
            if not is_ok:
                raise RateLimitException(
                    title="🙅‍♂️ Слишком много постов",
                    message="В последнее время вы создали слишком много постов. Потерпите, пожалуйста."
                )

        post = form.save(commit=False)
        if not post.author_id:
            post.author = request.me
        post.type = post_type
        post.html = None  # flush cache
        post.save()

        if mode == "create" or not post.is_visible:
            PostSubscription.subscribe(request.me, post, type=PostSubscription.TYPE_ALL_COMMENTS)

        if post.is_visible:
            if post.room:
                post.room.update_last_activity()

            SearchIndex.update_post_index(post)
            LinkedPost.create_links_from_text(post, post.text)

        action = request.POST.get("action")
        if action == "publish":
            post.publish()
            LinkedPost.create_links_from_text(post, post.text)

        return redirect("show_post", post.type, post.slug)

    return render(request, f"posts/compose/{post_type}.html", {
        "mode": mode,
        "post_type": post_type,
        "form": form,
    })
