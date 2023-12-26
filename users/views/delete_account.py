from datetime import datetime

from django.conf import settings
from django.shortcuts import redirect, render
from django_q.tasks import async_task

from authn.decorators.auth import require_auth
from authn.models.session import Session, Code
from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from club.exceptions import BadRequest, AccessDenied
from gdpr.models import DataRequests
from notifications.email.users import send_delete_account_request_email, send_delete_account_confirm_email
from payments.helpers import cancel_all_stripe_subscriptions


@require_auth
def request_delete_account(request):
    if request.method != "POST":
        return redirect("edit_account", "me", permanent=False)

    confirmation_string = request.POST.get("confirm")
    if confirmation_string != settings.GDPR_DELETE_CONFIRMATION:
        raise BadRequest(
            title="Неправильная строка подтверждения",
            message=f"Вы должны в точности написать \"{settings.GDPR_DELETE_CONFIRMATION}\" "
                    f"чтобы запустить процедуру удаления аккаунта"
        )

    DataRequests.register_forget_request(request.me)

    code = Code.create_for_user(user=request.me, recipient=request.me.email, length=settings.GDPR_DELETE_CODE_LENGTH)
    async_task(
        send_delete_account_request_email,
        user=request.me,
        code=code
    )

    return render(request, "users/messages/delete_account_requested.html", {"user": request.me})


@require_auth
def confirm_delete_account(request):
    confirmation_hash = request.POST.get("secret_hash")
    code = request.POST.get("code")
    if confirmation_hash != request.me.secret_hash or not code:
        raise AccessDenied(
            title="Что-то не сходится",
            message="Проверьте правильность кода и попробуйте запросить удаление аккаунта еще раз"
        )

    # verify code (raises an exception)
    Code.check_code(recipient=request.me.email, code=code)

    # cancel payments
    cancel_all_stripe_subscriptions(request.me.stripe_id)

    # mark user for deletion
    request.me.deleted_at = datetime.utcnow()
    request.me.save()

    # remove sessions
    Session.objects.filter(user=request.me).delete()

    # notify user
    async_task(
        send_delete_account_confirm_email,
        user=request.me,
    )

    # notify admins
    async_task(
        send_telegram_message,
        chat=ADMIN_CHAT,
        text=f"💀 Юзер удалился: {settings.APP_HOST}/user/{request.me.slug}/",
    )

    # an actual deletion will be done in a cron task ("manage.py delete_users")

    return render(request, "users/messages/delete_account_confirmed.html",)
