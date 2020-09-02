from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect

from auth.helpers import api_required
from posts.models.post import Post


@api_required
def md_show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    # drafts are visible only to authors and moderators
    if not post.is_visible:
        if not request.me or (request.me != post.author and not request.me.is_moderator):
            raise Http404()

    post_markdown = f"""# {post.title}\n\n{post.text}"""

    return HttpResponse(post_markdown, content_type="text/plain; charset=utf-8")


@api_required
def api_show_post(request, post_type, post_slug):
    post = get_object_or_404(Post, slug=post_slug)

    if post.type != post_type:
        return redirect("show_post", post.type, post.slug)

    # drafts are visible only to authors and moderators
    if not post.is_visible:
        if not request.me or (request.me != post.author and not request.me.is_moderator):
            raise Http404()

    return JsonResponse({
        "post": post.to_dict()
    }, json_dumps_params=dict(ensure_ascii=False))
