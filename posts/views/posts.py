from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from auth.helpers import check_user_permissions, auth_required
from club.exceptions import AccessDenied, ContentDuplicated, RateLimitException
from common.request import ajax_request
from posts.forms.compose import POST_TYPE_MAP, PostTextForm
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from posts.models.views import PostView
from posts.models.votes import PostVote
from posts.renderers import render_post
from search.models import SearchIndex
from users.models.user import User


def show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    # post_type can be changed by moderator
    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    # don't show private posts into public
    if not post.is_public:
        access_denied = check_user_permissions(request, post=post)
        if access_denied:
            return access_denied

    # drafts are visible only to authors and moderators
    if not post.is_visible:
        if not request.me or (request.me != post.author and not request.me.is_moderator):
            raise Http404()

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

    return render_post(request, post, {
        "post_last_view_at": last_view_at
    })


@auth_required
def edit_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)
    if post.author != request.me and not request.me.is_moderator:
        raise AccessDenied()

    PostFormClass = POST_TYPE_MAP.get(post.type) or PostTextForm

    if request.method == "POST":
        form = PostFormClass(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            if not post.author:
                post.author = request.me
            post.html = None  # flush cache
            post.save()

            SearchIndex.update_post_index(post)

            if post.is_visible:
                return redirect("show_post", post.type, post.slug)
            else:
                return redirect("compose")
    else:
        form = PostFormClass(instance=post)

    return render(request, f"posts/compose/{post.type}.html", {
        "mode": "edit",
        "form": form
    })


@auth_required
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


@auth_required
@ajax_request
def upvote_post(request, post_slug):
    if request.method != "POST":
        raise Http404()

    post = get_object_or_404(Post, slug=post_slug)

    post_vote, is_vote_created = PostVote.upvote(
        request=request,
        user=request.me,
        post=post,
    )

    return {
        "post": {
            "upvotes": post.upvotes + (1 if is_vote_created else 0),
        },
        "upvoted_timestamp": int(post_vote.created_at.timestamp() * 1000)
    }

@auth_required
@ajax_request
def retract_post_vote(request, post_slug):
    if request.method != "POST":
        raise Http404()

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


@auth_required
@ajax_request
def toggle_post_subscription(request, post_slug):
    if request.method != "POST":
        raise Http404()

    post = get_object_or_404(Post, slug=post_slug)

    subscription, is_created = PostSubscription.objects.get_or_create(
        user=request.me,
        post=post,
    )

    if not is_created:
        subscription.delete()

    return {
        "status": "created" if is_created else "deleted"
    }


@auth_required
def compose(request):
    drafts = Post.objects.filter(author=request.me, is_visible=False, deleted_at__isnull=True)[:100]
    return render(request, "posts/compose/compose.html", {
        "drafts": drafts
    })


@auth_required
def compose_type(request, post_type):
    if post_type not in dict(Post.TYPES):
        raise Http404()

    FormClass = POST_TYPE_MAP.get(post_type) or PostTextForm

    if request.method == "POST":
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():

            if not request.me.is_moderator:
                if Post.check_duplicate(user=request.me, title=form.cleaned_data["title"]):
                    raise ContentDuplicated()

                is_ok = Post.check_rate_limits(request.me)
                if not is_ok:
                    raise RateLimitException(
                        title="🙅‍♂️ Слишком много постов",
                        message="В последнее время вы создали слишком много постов. Потерпите, пожалуйста."
                    )

            post = form.save(commit=False)
            post.author = request.me
            post.type = post_type
            post.save()

            PostSubscription.subscribe(request.me, post)

            if post.is_visible:
                if post.topic:
                    post.topic.update_last_activity()

                SearchIndex.update_post_index(post)

                return redirect("show_post", post.type, post.slug)

            return redirect("compose")
    else:
        form = FormClass()

    return render(request, f"posts/compose/{post_type}.html", {
        "mode": "create",
        "form": form
    })
