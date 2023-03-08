from django.http import Http404, JsonResponse

from authn.decorators.api import api
from tags.models import Tag
from users.models.user import User

MIN_PREFIX_LENGTH = 3
MAX_PREFIX_LENGTH = 15


@api(require_auth=True)
def api_search_users(request):
    if request.method != "GET":
        raise Http404()

    prefix = request.GET.get("prefix", "")

    if len(prefix) < MIN_PREFIX_LENGTH or len(prefix) > MAX_PREFIX_LENGTH:
        return JsonResponse({
            "users": []
        })

    suggested_users = User.registered_members().filter(slug__startswith=prefix)[:5]

    return JsonResponse({
        "users": [{
            "slug": user.slug,
            "full_name": user.full_name
        } for user in suggested_users],
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
