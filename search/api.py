from django.conf import settings
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from club.exceptions import ApiBadRequest
from common.pagination import paginate
from posts.models.post import Post
from search.models import SearchIndex
from search.views import ALLOWED_ORDERING, ALLOWED_TYPES
from tags.models import Tag
from users.models.user import User

MIN_PREFIX_LENGTH = 3
MAX_PREFIX_LENGTH = 15
MAX_RESULTS = 25


@api(require_auth=True)
@require_http_methods(["GET"])
def api_search(request, content_type=None):
    query = (request.GET.get("q") or "").strip()
    if not query:
        raise ApiBadRequest(title="Пустой запрос", message="Передайте параметр q")

    results = SearchIndex.search(query).select_related(
        "post__author", "comment__author", "comment__post", "user"
    )

    content_type = content_type or request.GET.get("type")
    if content_type in ALLOWED_TYPES:
        results = results.filter(type=content_type)
    else:
        content_type = None

    # hack: exclude intros from posts page
    if content_type == SearchIndex.TYPE_POST:
        results = results.exclude(post__type=Post.TYPE_INTRO)

    results = results.exclude(comment__isnull=False, comment__is_deleted=True)
    results = results.exclude(post__visibility=Post.VISIBILITY_DRAFT).exclude(post__deleted_at__isnull=False)

    ordering = request.GET.get("ordering")
    if ordering not in ALLOWED_ORDERING:
        ordering = "-rank"

    results = results.order_by(ordering, "id")
    page = paginate(request, results, page_size=settings.SEARCH_PAGE_SIZE)

    items = []
    for result in page:
        if result.type == SearchIndex.TYPE_POST and result.post:
            items.append({
                "type": SearchIndex.TYPE_POST,
                "post": result.post.to_dict(including_private=bool(request.me)),
            })
        elif result.type == SearchIndex.TYPE_COMMENT and result.comment:
            items.append({
                "type": SearchIndex.TYPE_COMMENT,
                "comment": result.comment.to_dict(),
            })
        elif result.type == SearchIndex.TYPE_USER and result.user:
            items.append({
                "type": SearchIndex.TYPE_USER,
                "user": result.user.to_dict(),
            })

    return {
        "query": query,
        "type": content_type,
        "ordering": ordering,
        "page": page.number,
        "pages": page.paginator.num_pages,
        "results": items,
    }


@api(require_auth=True)
@require_http_methods(["GET"])
def api_search_users(request):
    prefix = request.GET.get("prefix", "")
    query = request.GET.get("q", "")
    users = []

    if prefix:
        if MIN_PREFIX_LENGTH <= len(prefix) < MAX_PREFIX_LENGTH:
            users = User.registered_members()\
                .filter(slug__istartswith=prefix)\
                .order_by("-last_activity_at")[:MAX_RESULTS]
    elif query:
        users = [
            result.user for result in (
                SearchIndex.search(query)
                .filter(type=SearchIndex.TYPE_USER)
                .order_by("-user__last_activity_at")
            ) if result.user
        ][:MAX_RESULTS]

    return {
        "users": [{
            "slug": user.slug,
            "full_name": user.full_name,
            "avatar": user.get_avatar(),
        } for user in users],
    }


@api(require_auth=True)
@require_http_methods(["GET"])
def api_search_tags(request):
    tags = Tag.objects.filter(is_visible=True)

    group = request.GET.get("group")
    if group:
        tags = tags.filter(group=group)

    prefix = request.GET.get("prefix")

    if prefix:
        if len(prefix) < MIN_PREFIX_LENGTH or len(prefix) > MAX_PREFIX_LENGTH:
            return {
                "tags": []
            }

        tags = tags.filter(name__icontains=prefix)

    return {
        "tags": [
            tag.to_dict() for tag in tags
        ]
    }
