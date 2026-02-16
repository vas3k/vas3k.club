from authn.decorators.api import api
from common.pagination import paginate
from posts.models.post import Post


@api(require_auth=True)
def api_bookmarks(request):
    posts = Post.objects_for_user(request.me)\
        .filter(bookmarks__user=request.me, deleted_at__isnull=True)\
        .order_by('-bookmarks__created_at')

    page = paginate(request, posts)

    return {
        "posts": [post.to_dict(including_private=True) for post in page],
        "page": page.number,
        "total_pages": page.paginator.num_pages,
        "has_next": page.has_next(),
    }
