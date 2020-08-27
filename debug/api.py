from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from debug.utils_for_tests import todict
from users.models.user import User


def api_me(request):
    response = {}

    if request.me:
        user: User = get_object_or_404(User, slug=request.me.slug)
        response = todict(user)
        response["is_authorised"] = True
    else:
        response["is_authorised"] = False

    return JsonResponse(response)
