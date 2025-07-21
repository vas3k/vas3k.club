from django import forms
from django.shortcuts import render

from notifications.email.users import send_ping_email
from notifications.telegram.users import notify_user_ping, notify_admin_user_ping
from users.models.user import User


class UserPingForm(forms.Form):
    ping = forms.CharField(
        label="Отправить сообщение",
        max_length=5000,
        widget=forms.Textarea(),
        required=False,
    )


def get_ping_action(request, user: User, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": UserPingForm(),
    })


def post_ping_action(request, user: User, **context):
    form = UserPingForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Ping
        if data["ping"]:
            send_ping_email(user, message=data["ping"])
            notify_user_ping(user, message=data["ping"])
            notify_admin_user_ping(user, message=data["ping"])

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Юзера {user.full_name} пинганули",
            "message": f"Он получит сообщение на почту и в телеграм",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": user,
            "form": form,
        })

