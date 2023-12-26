from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django_q.tasks import async_task

from authn.decorators.api import api
from club.exceptions import ApiAccessDenied
from notifications.email.invites import send_invite_renewed_email
from payments.helpers import gift_membership_days
from users.models.user import User


@api(require_auth=True)
@require_POST
def api_gift_days(request, days, user_slug):
    from_user = request.me
    to_user = get_object_or_404(User, slug=user_slug)

    if not from_user.is_bank:
        raise ApiAccessDenied(message="Только юзеры с ролью 'bank' могут переводить дни")

    gift_membership_days(
        days=days,
        from_user=from_user,
        to_user=to_user,
        deduct_from_original_user=True,
    )

    async_task(send_invite_renewed_email, request.me, to_user)

    return JsonResponse({
        "status": "success",
    })

