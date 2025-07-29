from django.conf import settings
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django_q.tasks import async_task

from authn.helpers import set_session_cookie
from authn.models.session import Session, Code
from notifications.email.users import send_auth_email
from notifications.telegram.users import notify_user_auth
from users.models.user import User


def email_login(request):
    if request.method != "POST":
        return redirect("login")

    goto = request.POST.get("goto")
    email_or_login = request.POST.get("email_or_login")
    if not email_or_login:
        return redirect("login")

    email_or_login = email_or_login.strip()

    user = User.objects.filter(Q(email=email_or_login.lower()) | Q(slug=email_or_login)).first()
    if not user:
        return render(request, "error.html", {
            "title": "Такого юзера нет 🤔",
            "message": "Пользователь с такой почтой не найден в списке членов Клуба. "
                       "Попробуйте другую почту или никнейм. "
                       "Если совсем ничего не выйдет, напишите нам, попробуем помочь.",
        }, status=404)

    code = Code.create_for_user(user=user, recipient=user.email, length=settings.AUTH_CODE_LENGTH)
    async_task(send_auth_email, user, code)
    async_task(notify_user_auth, user, code)

    return render(request, "auth/email.html", {
        "email": user.email,
        "goto": goto,
        "restore": user.deleted_at is not None,
    })


def email_login_code(request):
    email = request.GET.get("email")
    code = request.GET.get("code")
    if not email or not code:
        return redirect("login")

    goto = request.GET.get("goto")
    email = email.lower().strip()
    code = code.lower().strip()

    user = Code.check_code(recipient=email, code=code)
    session = Session.create_for_user(user)

    if not user.is_email_verified:
        # save 1 click and verify email
        user.is_email_verified = True
        user.save()

    if user.deleted_at:
        # cancel user deletion
        user.deleted_at = None
        user.save()

    redirect_to = reverse("profile", args=[user.slug]) if not goto else goto
    response = redirect(redirect_to)
    return set_session_cookie(response, user, session)
