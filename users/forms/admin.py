from django import forms
from django.forms import ModelForm

from common.data.achievements import ACHIEVEMENTS
from common.data.ban import TEMPORARY_BAN_REASONS, PERMANENT_BAN_REASONS
from common.data.hats import HATS
from common.forms import ImageUploadField
from users.models.user import User


class UserAdminForm(forms.Form):
    role_action = forms.ChoiceField(
        label="Выбрать действие",
        choices=[(None, "---"), ("add", "Добавить роль"), ("delete", "Удалить роль")],
        required=False,
    )

    role = forms.ChoiceField(
        label="Выбрать роль",
        choices=[(None, "---")] + User.ROLES,
        required=False,
    )

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

    is_temporarily_banned = forms.BooleanField(
        label="Забанить временно",
        required=False
    )

    temporary_ban_reason = forms.ChoiceField(
        label="Причина",
        choices=[(key, f"{reason.name} ({reason.min_duration}+ дней)") for key, reason in TEMPORARY_BAN_REASONS.items()],
        required=False,
    )

    is_permanently_banned = forms.BooleanField(
        label="Забанить навечно",
        required=False
    )

    permanent_ban_reason = forms.ChoiceField(
        label="Причина",
        choices=[(key, reason.name) for key, reason in PERMANENT_BAN_REASONS.items()],
        required=False,
    )

    is_custom_banned = forms.BooleanField(
        label="Забанить кастомно",
        required=False
    )

    custom_ban_days = forms.IntegerField(
        label="Бан истечет через N дней",
        initial=5,
        required=False
    )

    custom_ban_name = forms.CharField(
        label="Короткая причина",
        max_length=80,
        required=False,
    )

    custom_ban_reason = forms.CharField(
        label="Развернутый комментарий и ссылки (опционально)",
        max_length=5000,
        required=False,
        widget=forms.Textarea(attrs={"maxlength": 5000}),
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

    add_membership_days = forms.IntegerField(
        label="Добавить дней членства",
        required=False
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
    company = forms.CharField(
        label="Компания",
        required=False,
        max_length=128,
    )
    position = forms.CharField(
        label="Должность",
        required=False,
        max_length=128,
    )
    contact = forms.CharField(
        label="Контакт для связи",
        required=False,
        max_length=256,
    )
    membership_platform_type = forms.ChoiceField(
        label="Тип платформы подписки",
        choices=User.MEMBERSHIP_PLATFORMS,
        required=True,
    )
    email_digest_type = forms.ChoiceField(
        label="Тип email-дайджеста",
        required=True,
        choices=User.EMAIL_DIGEST_TYPES,
    )
    telegram_id = forms.CharField(
        label="Телеграм",
        required=False,
        max_length=128
    )
    stripe_id = forms.CharField(
        label="Страйп",
        required=False,
        max_length=128
    )
    is_email_verified = forms.BooleanField(
        label="Статус активации email",
        required=False
    )
    is_banned_until = forms.DateTimeField(
        label="Бан истечет",
        help_text="Например: 23.01.2022 01:09:31",
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "slug",
            "full_name",
            "email",
            "company",
            "position",
            "contact",
            "membership_platform_type",
            "email_digest_type",
            "telegram_id",
            "stripe_id",
            "is_email_verified",
            "is_banned_until",
        ]

    def clean_email(self):
        return self.cleaned_data["email"].lower()
