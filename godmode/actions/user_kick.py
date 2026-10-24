from django import forms
from django.shortcuts import render
from django_q.tasks import async_task

from rooms.helpers import ban_user_in_all_chats
from users.models.user import User


class UserKickForm(forms.Form):
    kick_from_chats = forms.BooleanField(
        label="Кикнуть из всех чатов",
        help_text="Выгнать, но не забанить",
    )


def get_kick_action(request, user: User, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": UserKickForm(),
    })


def post_kick_action(request, user: User, **context):
    form = UserKickForm(request.POST)

    if form.is_valid():
        if not user.telegram_id:
            form.add_error("kick_from_chats", "У пользователя не привязан Telegram.")
        else:
            async_task(ban_user_in_all_chats, user, is_permanent=False)

            return render(request, "godmode/message.html", {
                **context,
                "title": f"Кикаем {user.full_name}",
                "message": "Бот удалит пользователя из чатов, но не забанит. Он сможет вернуться. Все ок?",
            })

    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": form,
    })
