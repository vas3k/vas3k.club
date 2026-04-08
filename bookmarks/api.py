from authn.decorators.api import api
from bookmarks.helpers import get_user_bookmarks
from common.pagination import paginate


@api(require_auth=True)
def api_bookmarks(request):
    posts = get_user_bookmarks(request.me)
    page = paginate(request, posts)

    return {
        "posts": [post.to_dict() for post in page],
        "page": page.number,
        "total_pages": page.paginator.num_pages,
        "has_next": page.has_next(),
    }
