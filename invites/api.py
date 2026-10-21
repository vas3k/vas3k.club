from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from club.exceptions import ApiAccessDenied
from common.api import API
from invites.models import Invite
from payments.models import Payment
from payments.products import PRODUCTS
from utils.strings import random_string


@api(require_auth=True)
@require_http_methods(["GET", "POST"])
def api_gift_invite_link(request):
    if request.method == "GET":
        user_invites = Invite.for_user(user=request.me)
        return {
            "invites": [invite.to_dict() for invite in user_invites],
        }

    if not request.me.is_god:
        raise ApiAccessDenied(message="Только администраторы могут генерировать инвайты")

    data = API.parse_body(request)
    reference = str(data.get("reference") or "admin-" + random_string(length=16))
    telegram_user_id = str(data["telegram_user_id"]) if data.get("telegram_user_id") is not None else None

    invite = Invite.objects.create(
        user=request.me,
        payment=Payment.create(
            reference=reference,
            user=request.me,
            product=PRODUCTS["club1_invite"],
            status=Payment.STATUS_SUCCESS,
            data={
                "source": "admin",
                "telegram_user_id": telegram_user_id
            }
        )
    )

    return {
        "invite": invite.to_dict(),
    }
