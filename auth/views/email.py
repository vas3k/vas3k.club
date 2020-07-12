from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse

from auth.helpers import set_session_cookie
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
    user = User.objects.filter(Q(email=email) | Q(slug=email)).first()
    if not user:
        return render(request, "error.html", {
            "title": "Такого юзера нет 🤔",
            "message": "Пользователь с такой почтой не найден в списке членов Клуба. "
                       "Попробуйте другую почту или никнейм. "
                       "Если совсем ничего не выйдет, напишите нам на club@vas3k.club, попробуем помочь.",
        })

    code = Code.create_for_user(user=user, recipient=email)

    send_auth_email(user, code)

    return render(request, "auth/email.html", {
        "email": email,
        "goto": request.POST.get("goto"),
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

    redirect_to = reverse("profile", args=[user.slug]) if not goto else goto
    response = redirect(redirect_to)
    return set_session_cookie(response, user, session)
