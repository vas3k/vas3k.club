from django.http import JsonResponse
from django.shortcuts import get_object_or_404

from auth.helpers import api_required
from club.exceptions import ApiAccessDenied
from users.models.user import User
import json

@api_required
def api_profile(request, user_slug):
    if user_slug == "me":
        user_slug = request.me.slug

    user = get_object_or_404(User, slug=user_slug)

    if request.me.moderation_status != User.MODERATION_STATUS_APPROVED and request.me.id != user.id:
        raise ApiAccessDenied(title="Non-approved users can only access their own profiles")

    return JsonResponse({
        "user": user.to_dict()
    })


def api_telegram_exist(request):
    if request.method == "GET":
        try:
            json_data = json.loads(request.body)
            telegram_id = json_data["telegram_id"]
            user = User.objects.get(telegram_id=telegram_id)
            if user.is_banned:
                return JsonResponse({ "user": "BANNED" })
            return JsonResponse({ "user": "ACTIVE" })
        except User.DoesNotExist:
            return JsonResponse({ "user": "NOT FOUND" })
        except:
            raise ApiAccessDenied(title="Please provide correct body")
