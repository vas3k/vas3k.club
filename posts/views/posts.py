from django.conf import settings
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django_q.tasks import async_task

from authn.helpers import check_user_permissions
from authn.decorators.auth import require_auth
from club.exceptions import AccessDenied, ContentDuplicated, RateLimitException
from notifications.telegram.posts import send_published_post_to_moderators, notify_author_friends, \
    announce_in_online_channel, send_intro_changes_to_moderators, notify_post_label_changed, \
    notify_post_coauthors_changed
from posts.forms.compose import POST_TYPE_MAP, PostTextForm
from posts.models.linked import LinkedPost
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from posts.models.views import PostView
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
    linked_posts = [p for p in linked_posts if not p.is_draft]

    return render_post(request, post, {
        "post_last_view_at": last_view_at,
        "linked_posts": linked_posts,
    })


@require_auth
def unpublish_post(request, post_slug):
    if request.method != "POST":
        return render(request, "confirm.html", {
            "title": f"Перенести пост в черновики?",
            "message": "Пост больше не будет виден в фиде, но останется у вас в черновиках",
            "button": "Да, в черновики его!"
        })

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
    if request.method != "POST":
        return render(request, "confirm.html", {
            "title": f"Очистить пост?",
            "message": "Контент поста будет удален, а автор анонимизирован. "
                       "От поста останется только заголовок и комментарии под ним",
            "button": "Очищаем!"
        })

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
        if request.method != "POST":
            return render(request, "confirm.html", {
                "title": f"Восстановить пост?",
                "message": "Он снова появится у вас в черновиках",
                "button": "Да, восстанавливаем"
            })

        post.undelete()
    else:
        # delete post
        if request.method != "POST":
            return render(request, "confirm.html", {
                "title": f"Удалить пост?",
                "message": "Он пропадёт с главной и из ваших черновиков",
                "button": "Да, удаляем"
            })

        post.delete()

    return redirect("compose")


@require_auth
def compose(request):
    drafts = Post.objects\
        .filter(visibility=Post.VISIBILITY_DRAFT, deleted_at__isnull=True)\
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

    if post_type == Post.TYPE_DOCS and not request.me.is_god:
        raise AccessDenied("Вы не можете создавать или редактировать доки :(")

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

        # create new post
        if mode == "create" or post.is_draft:
            PostSubscription.subscribe(request.me, post, type=PostSubscription.TYPE_ALL_COMMENTS)

        # publish post for the first time
        action = request.POST.get("action")
        if action == "publish":
            post.publish()

            async_task(send_published_post_to_moderators, post=post)
            async_task(notify_author_friends, post=post)
            async_task(announce_in_online_channel, post=post)

        # update post and room stats
        if post.visibility != Post.VISIBILITY_DRAFT:
            if post.room:
                post.room.update_last_activity()

            SearchIndex.update_post_index(post)
            LinkedPost.create_links_from_text(post, post.text)

        # track label and coauthors changes
        if "label_code" in form.changed_data:
            async_task(notify_post_label_changed, post)

        if "coauthors" in form.changed_data:
            async_task(notify_post_coauthors_changed, post)

        # track intro changes
        if post.type == Post.TYPE_INTRO and not post.is_draft:
            async_task(send_intro_changes_to_moderators, post=post)

        return redirect("show_post", post.type, post.slug)

    return render(request, f"posts/compose/{post_type}.html", {
        "mode": mode,
        "post_type": post_type,
        "form": form,
    })
