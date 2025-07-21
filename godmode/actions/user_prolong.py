from django import forms
from django.shortcuts import render

from notifications.telegram.common import send_telegram_message, ADMIN_CHAT
from payments.helpers import gift_membership_days
from users.models.user import User


class UserProlongForm(forms.Form):
    add_membership_days = forms.IntegerField(
        label="Добавить дней членства",
        required=True
    )



def get_prolong_action(request, user: User, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": UserProlongForm(),
    })


def post_prolong_action(request, user: User, **context):
    form = UserProlongForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Add more days of membership
        if data["add_membership_days"] and int(data["add_membership_days"]) > 0:
            gift_membership_days(
                days=data["add_membership_days"],
                from_user=request.me,
                to_user=user,
                deduct_from_original_user=False,
            )

            send_telegram_message(
                chat=ADMIN_CHAT,
                text=f"🎁 <b>Юзеру {user.slug} добавили {data['add_membership_days']} дней членства</b>",
            )

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Юзеру {user.full_name} добавили {data['add_membership_days']} дней членства",
            "message": f"Заслужил 👍",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": user,
            "form": form,
        })

