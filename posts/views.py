from datetime import datetime, timedelta

from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from auth.helpers import auth_required, moderator_role_required
from bot.common import render_html_message
from club.exceptions import AccessDenied, ContentDuplicated, RateLimitException
from comments.forms import CommentForm
from comments.models import Comment
from common.pagination import paginate
from common.request import ajax_request
from notifications.telegram.posts import announce_in_club_channel
from posts.admin import do_post_admin_actions
from posts.forms.admin import PostAdminForm, PostAnnounceForm
from posts.forms.compose import PostTextForm, POST_TYPE_MAP
from posts.helpers import extract_some_image
from posts.models import Post, Topic, PostVote, PostView
from posts.renderers import render_post


@auth_required
def feed(request, post_type=None, topic_slug=None, ordering="activity"):
    if request.me:
        request.me.update_last_activity()
        posts = Post.objects_for_user(request.me)
    else:
        posts = Post.visible_objects()

    # filter posts by type
    if post_type:
        posts = posts.filter(type=post_type)

    # filter by topic
    topic = None
    if topic_slug:
        topic = get_object_or_404(Topic, slug=topic_slug)
        posts = posts.filter(topic=topic)

    # hide non-public posts and intros from unauthorized users
    if not request.me:
        posts = posts.exclude(is_public=False).exclude(type=Post.TYPE_INTRO)

    # exclude shadow banned posts
    if request.me:
        posts = posts.exclude(Q(is_shadow_banned=True) & ~Q(author_id=request.me.id))

    # no type and topic? probably it's the main page, let's apply some more filters
    if not topic and not post_type:
        posts = posts.filter(is_visible_on_main_page=True)

    # order posts by some metric
    if ordering:
        if ordering == "activity":
            posts = posts.order_by("-last_activity_at")
        elif ordering == "new":
            posts = posts.order_by("-created_at")
        elif ordering == "top":
            posts = posts.filter(
                created_at__gte=datetime.utcnow() - timedelta(days=60)
            ).order_by("upvotes")
        else:
            raise Http404()

    # split results into pinned and unpinned posts
    pinned_posts = posts.filter(is_pinned_until__gte=datetime.utcnow())
    posts = posts.exclude(id__in=[p.id for p in pinned_posts])

    return render(request, "posts/feed.html", {
        "posts": paginate(request, posts),
        "pinned_posts": pinned_posts,
        "post_type": post_type,
        "ordering": ordering,
        "topic": topic,
    })


def show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, type=post_type, slug=post_slug)

    # don't show private posts into public
    if not post.is_public and not request.me:
        return render(request, "auth/access_denied.html")

    # drafts are visible only to authors and moderators
    if not post.is_visible and request.me != post.author and not request.me.is_moderator:
        raise Http404()

    # record a new view
    if request.me:
        request.me.update_last_activity()
        PostView.create_or_update(
            request=request,
            user=request.me,
            post=post,
        )

    return render_post(request, post)


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
@ajax_request
def upvote_post(request, post_slug):
    if request.method != "POST":
        raise Http404()

    post = get_object_or_404(Post, slug=post_slug)

    _, is_vote_created = PostVote.upvote(
        request=request,
        user=request.me,
        post=post,
    )

    return {
        "post": {
            "upvotes": post.upvotes + (1 if is_vote_created else 0)
        }
    }


@auth_required
def compose(request):
    drafts = Post.objects.filter(author=request.me, is_visible=False)[:100]
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

            if post.is_visible:
                if post.topic:
                    post.topic.update_last_activity()

                return redirect("show_post", post.type, post.slug)

            return redirect("compose")
    else:
        form = FormClass()

    return render(request, f"posts/compose/{post_type}.html", {
        "mode": "create",
        "form": form
    })


@auth_required
@moderator_role_required
def admin_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if request.method == "POST":
        form = PostAdminForm(request.POST)
        if form.is_valid():
            return do_post_admin_actions(request, post, form.cleaned_data)
    else:
        form = PostAdminForm()

    return render(request, "admin/simple_form.html", {
        "title": "Админить пост",
        "post": post,
        "form": form
    })


@auth_required
@moderator_role_required
def announce_post(request, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    initial = {
        "text": render_html_message("channel_post_announce.html", post=post),
        "image": extract_some_image(post),
    }

    if request.method == "POST":
        form = PostAnnounceForm(request.POST, initial=initial)
        if form.is_valid():
            announce_in_club_channel(
                post=post,
                announce_text=form.cleaned_data["text"],
                image=form.cleaned_data["image"] if form.cleaned_data["with_image"] else None
            )
            return render(request, "message.html", {
                "title": "Запощено ✅"
            })
    else:
        form = PostAnnounceForm(initial=initial)

    return render(request, "admin/simple_form.html", {
        "title": "Анонсировать пост на канале",
        "post": post,
        "form": form
    })
