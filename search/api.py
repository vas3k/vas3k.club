from django.http import Http404, JsonResponse
from django.forms.models import model_to_dict

from search.models import SearchIndex
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

@api(require_auth=True)
def api_search_users_full(request):
    if request.method != "GET":
        raise Http404()

    query = request.GET.get("query", "").strip()

    if not query:
        return JsonResponse({
            "users": []
        })

    search_results = SearchIndex.search(query).filter(type=SearchIndex.TYPE_USER).order_by("-rank")[:100]

    user_ids = search_results.values_list("user_id", flat=True)

    users = User.objects.filter(id__in=user_ids)

    fields_to_include = [
        "id", "slug", "full_name", "email", "bio",
        "company", "country", "city", "contact"
    ]

    user_data = []

    for user in users:
        user_dict = model_to_dict(user, fields=fields_to_include)
        user_data.append(user_dict)

    return JsonResponse({
        "users": user_data
    })