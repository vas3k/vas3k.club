from django import forms
from django.forms import ModelForm

from common.data.achievements import ACHIEVEMENTS
from common.data.hats import HATS
from common.forms import ImageUploadField
from users.models.user import User


class UserAdminForm(forms.Form):
    add_hat = forms.BooleanField(label="Выдать новую шапку", required=False)
    new_hat = forms.ChoiceField(
        label="Выбрать из популярных",
        choices=[(None, "---")] + [(key, value.get("title")) for key, value in HATS.items()],
        required=False,
    )
    new_hat_name = forms.CharField(
        label="Создать новый титул",
        max_length=48,
        required=False
    )
    new_hat_icon = ImageUploadField(
        label="Иконка",
        required=False,
        resize=(256, 256),
    )
    new_hat_color = forms.CharField(
        label="Цвет",
        initial="#000000",
        max_length=16,
        required=False
    )
    remove_hat = forms.BooleanField(
        label="Удалить текущую шапку",
        required=False
    )

    new_achievement = forms.ChoiceField(
        label="Выдать новую ачивку",
        choices=[(None, "---")] + [(key, value.get("name")) for key, value in ACHIEVEMENTS],
        required=False,
    )

    is_banned = forms.BooleanField(
        label="Забанить",
        required=False
    )
    ban_days = forms.IntegerField(
        label="Бан истечет через N дней",
        initial=5,
        required=False
    )
    ban_reason = forms.CharField(
        label="Причина бана",
        max_length=128,
        required=False
    )

    is_unbanned = forms.BooleanField(
        label="Разбанить",
        required=False
    )

    is_rejected = forms.BooleanField(
        label="Размодерирвать",
        required=False
    )

    delete_account = forms.BooleanField(
        label="Удалить аккаунт и обнулить подписку",
        required=False
    )

    ping = forms.CharField(
        label="Отправить сообщение",
        max_length=5000,
        widget=forms.Textarea(),
        required=False,
    )


class UserInfoAdminForm(ModelForm):
    slug = forms.CharField(
        label="Никнейм",
        required=True,
        max_length=32,
        min_length=3,
        widget=forms.TextInput(attrs={
            "pattern": "[A-Za-z0-9_-]+",
            "minlength": 3,
        }),
    )
    full_name = forms.CharField(
        label="Имя и фамилия",
        required=True,
        max_length=128
    )
    email = forms.EmailField(
        label="E-mail",
        required=True
    )

    class Meta:
        model = User
        fields = [
            "slug",
            "full_name",
            "email",
        ]
