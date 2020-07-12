from django.conf import settings
from django.shortcuts import redirect, render
from django.urls import reverse

from auth.models import Session, Code
from notifications.email.users import send_auth_email
from users.models.user import User


def email_login(request):
    if request.method != "POST":
        return redirect("login")

    email = request.POST.get("email")
    if not email:
        return redirect("login")

    email = email.lower().strip()
    user = User.objects.filter(email=email).first()
    if not user:
        return render(request, "error.html", {
            "title": "Такого юзера нет 🤔",
            "message": "Пользователь с такой почтой не найден среди членов клуба",
        })

    code = Code.create_for_user(user=user, recipient=email)

    send_auth_email(user, code)

    return render(request, "auth/email.html", {"email": email, "goto": request.POST.get("goto")})


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

    redirect_to = reverse("profile", args=[user.slug]) if not goto else goto
    response = redirect(redirect_to)
    response.set_cookie(
        key="token",
        value=session.token,
        expires=user.membership_expires_at,
        httponly=True,
        secure=not settings.DEBUG,
    )
    return response
