from django.http import Http404, JsonResponse

from auth.helpers import api_required
from users.models.user import User

MIN_PREFIX_LENGTH = 3
MAX_PREFIX_LENGTH = 20


@api_required
def api_search_users(request):
    if request.method != "GET":
        raise Http404()

    prefix = request.GET.get("prefix", "")

    if len(prefix) < MIN_PREFIX_LENGTH or len(prefix) > MAX_PREFIX_LENGTH:
        return {
            "users": []
        }

    suggested_users = User.registered_members().filter(slug__startswith=prefix)[:5]

    return JsonResponse({
        "users": [{
            "slug": user.slug,
            "full_name": user.full_name
        } for user in suggested_users],
    })
