from django import forms
from django.shortcuts import render

from users.models.user import User
from users.utils import is_role_manageable_by_user


class UserRoleForm(forms.Form):
    role_action = forms.ChoiceField(
        label="Выбрать действие",
        choices=[(None, "---"), ("add", "Добавить роль"), ("delete", "Удалить роль")],
        required=True,
    )

    role = forms.ChoiceField(
        label="Выбрать роль",
        choices=[(None, "---")] + User.ROLES,
        required=True,
    )


def get_role_action(request, user: User, **context):
    return render(request, "godmode/action.html", {
        **context,
        "item": user,
        "form": UserRoleForm(),
    })


def post_role_action(request, user: User, **context):
    form = UserRoleForm(request.POST, request.FILES)
    if form.is_valid():
        data = form.cleaned_data

        # Roles
        if data["role"] and is_role_manageable_by_user(data["role"], request.me):
            role = data["role"]

            if data["role_action"] == "add" and role not in user.roles:
                user.roles.append(role)
                user.save()
                return render(request, "godmode/message.html", {
                    **context,
                    "title": f"Юзеру {user.full_name} выдали роль {role}",
                    "message": f"Ура 🎉",
                })

            if data["role_action"] == "delete" and role in user.roles:
                user.roles.remove(role)
                user.save()
                return render(request, "godmode/message.html", {
                    **context,
                    "title": f"У юзера {user.full_name} отобрали роль {role}",
                    "message": f"Ура 🎉",
                })

        return render(request, "godmode/message.html", {
            **context,
            "title": f"Ничего не произошло...",
            "message": f"Странна",
        })
    else:
        return render(request, "godmode/action.html", {
            **context,
            "item": user,
            "form": form,
        })

