from django.http import Http404, JsonResponse

from authn.decorators.api import api
from search.models import SearchIndex
from tags.models import Tag
from users.models.user import User

MIN_PREFIX_LENGTH = 3
MAX_PREFIX_LENGTH = 15
MAX_RESULTS = 25


@api(require_auth=True)
def api_search_users(request):
    if request.method != "GET":
        raise Http404()

    prefix = request.GET.get("prefix", "")
    query = request.GET.get("q", "")
    users = []

    if prefix:
        if MIN_PREFIX_LENGTH <= len(prefix) < MAX_PREFIX_LENGTH:
            users = User.registered_members()\
                .filter(slug__istartswith=prefix)\
                .order_by("-last_activity_at")[:MAX_RESULTS]
    elif query:
        users = [r.user for r in SearchIndex\
            .search(query)\
            .filter(type=SearchIndex.TYPE_USER)\
            .order_by("-user__last_activity_at") if r.user][:MAX_RESULTS]

    return JsonResponse({
        "users": [{
            "slug": user.slug,
            "full_name": user.full_name,
            "avatar": user.get_avatar(),
        } for user in users],
    })


@api(require_auth=True)
def api_search_tags(request):
    tags = Tag.objects.filter(is_visible=True)

    group = request.GET.get("group")
    if group:
        tags = tags.filter(group=group)

    prefix = request.GET.get("prefix")

    if prefix:
        if len(prefix) < MIN_PREFIX_LENGTH or len(prefix) > MAX_PREFIX_LENGTH:
            return JsonResponse({
                "tags": []
            })

        tags = tags.filter(name__icontains=prefix)

    return JsonResponse({
        "tags": [
            tag.to_dict() for tag in tags
        ]
    })
