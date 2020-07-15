from django import forms

from common.data.achievements import ACHIEVEMENTS
from common.data.hats import HATS
from common.forms import ImageUploadField


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

    ping = forms.CharField(
        label="Отправить сообщение",
        max_length=5000,
        widget=forms.Textarea(),
        required=False,
    )
