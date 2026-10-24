from django import forms
from django.shortcuts import render
from django_q.tasks import async_task

from rooms.helpers import ban_user_in_all_chats
from users.models.user import User


class UserKickForm(forms.Form):
    kick_from_chats = forms.BooleanField(
        label="Кикнуть из всех чатов",
        help_text="Удалить из чатов временным баном на 5 минут. После этого пользователь сможет вступить заново. "
                  "Аккаунт и подписка останутся без изменений. "
                  "Перед удалением администратор чата будет разжалован; его права автоматически не восстановятся.",
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
                "title": f"Кик {user.full_name} поставлен в очередь",
                "message": "Бот удалит пользователя из чатов, где у него есть права на удаление участников. "
                           "Через 5 минут пользователь сможет вступить заново. "
                           "Существующие баны будут пропущены. Удаление администраторов зависит от прав бота. "
                           "Временный бан поддерживается только в супергруппах и каналах.",
            })

    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": form,
    })
