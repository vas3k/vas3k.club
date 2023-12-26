from django.conf import settings
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from authn.helpers import check_user_permissions
from authn.decorators.api import api
from club.exceptions import ApiAuthRequired
from common.pagination import paginate
from posts.models.post import Post
from posts.helpers import POST_TYPE_ALL, ORDERING_ACTIVITY, sort_feed


@api(require_auth=False)
def md_show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    if not post.can_view(request.me):
        raise Http404()

    # don't show private posts into public
    if not post.is_public:
        access_denied = check_user_permissions(request, post=post)
        if access_denied:
            raise ApiAuthRequired()

    post_markdown = f"""# {post.title}\n\n{post.text}"""

    return HttpResponse(post_markdown, content_type="text/plain; charset=utf-8")


@api(require_auth=False)
def api_show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    if not post.can_view(request.me):
        raise Http404()

    return {
        "post": post.to_dict(including_private=bool(request.me))
    }


@api(require_auth=False)
def json_feed(request, post_type=POST_TYPE_ALL, ordering=ORDERING_ACTIVITY):
    page_number = int(request.GET.get("page") or 1)
    posts = Post.visible_objects()

    # filter posts by type
    if post_type != POST_TYPE_ALL:
        posts = posts.filter(type=post_type)

    # order posts by some metric
    posts = sort_feed(posts, ordering)

    # paginate
    posts = paginate(request, posts)

    return JsonResponse({
        "version": "https://jsonfeed.org/version/1.1",
        "title": settings.APP_NAME,
        "home_page_url": settings.APP_HOST,
        "feed_url": f"{settings.APP_HOST}{reverse('json_feed')}",
        "next_url": f"{settings.APP_HOST}{reverse('json_feed')}?page={page_number + 1}",
        "items": [
            post.to_dict(including_private=bool(request.me)) for post in posts
        ]
    }, json_dumps_params=dict(ensure_ascii=False), content_type="application/feed+json")
