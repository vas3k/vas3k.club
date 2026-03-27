from django import forms
from django.shortcuts import render

from notifications.email.users import send_unmoderated_email
from notifications.telegram.users import notify_admin_user_unmoderate
from users.models.user import User


class UserUnmoderateForm(forms.Form):
    is_rejected = forms.BooleanField(
        label="Размодерирвать",
        required=True
    )

def get_unmoderate_action(request, user: User, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": UserUnmoderateForm(),
    })


def post_unmoderate_action(request, user: User, **context):
    form = UserUnmoderateForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Unmoderate
        if data["is_rejected"]:
            user.moderation_status = User.MODERATION_STATUS_REJECTED
            user.save()
            send_unmoderated_email(user)
            notify_admin_user_unmoderate(user)

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Юзера {user.full_name} размодерировали",
            "message": f"Теперь ждем когда он перепишет интро",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": user,
            "form": form,
        })

