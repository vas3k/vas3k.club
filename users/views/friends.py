from django.http import Http404
from django.shortcuts import get_object_or_404

from auth.helpers import auth_required
from common.request import ajax_request
from users.models.friends import Friend
from users.models.user import User


@auth_required
@ajax_request
def toggle_friend(request, user_slug):
    if request.method != "POST":
        raise Http404()

    user_to = get_object_or_404(User, slug=user_slug)

    friend, is_created = Friend.add_friend(
        user_from=request.me,
        user_to=user_to,
    )

    if not is_created:
        Friend.delete_friend(
            user_from=request.me,
            user_to=user_to,
        )

    return {
        "status": "created" if is_created else "deleted",
    }
