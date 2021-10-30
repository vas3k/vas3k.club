from django.http import Http404

from auth.helpers import auth_required
from common.request import ajax_request
from users.models.user import User

@auth_required
@ajax_request
def suggest_users(request):
    if request.method != "GET":
        raise Http404()

    sample = request.GET.get('sample', '')

    if len(sample) < 1:
        return {
            "suggested_users": []
        }

    suggested_users = User.registered_members().filter(slug__startswith=sample)[:5]

    return {
        "suggested_users": [
            user.slug
            for user in suggested_users.all()
        ],
    }
