from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from common.data.countries import COUNTRIES
from common.data.expertise import EXPERTISE
from users.models.user import User
from users.models.expertise import UserExpertise
from utils.forms import ImageUploadField


class UserEditForm(ModelForm):
    full_name = forms.CharField(
        label="Имя",
        required=True,
        max_length=128
    )
    avatar = ImageUploadField(
        label="Обновить аватар",
        required=False,
        resize=(512, 512),
        convert_to="jpg",
    )
    city = forms.CharField(
        label="город",
        required=True,
        max_length=120
    )
    country = forms.ChoiceField(
        label="Страна",
        choices=COUNTRIES,
        required=True
    )
    bio = forms.CharField(
        label="Ссылочки на себя и всякое такое",
        required=False,
        max_length=256,
        widget=forms.Textarea(attrs={"maxlength": 256}),
    )
    company = forms.CharField(
        label="Компания",
        required=False,
        max_length=128
    )
    position = forms.CharField(
        label="Должность или что вы делаете",
        required=True,
        max_length=128
    )
    contact = forms.CharField(
        label="Контакт для связи",
        required=False,
        max_length=256,
    )

    class Meta:
        model = User
        fields = [
            "full_name",
            "avatar",
            "company",
            "position",
            "city",
            "country",
            "bio",
            "contact",
        ]


class NotificationsEditForm(ModelForm):
    email_digest_type = forms.ChoiceField(
        label="Тип email-дайджеста",
        required=True,
        choices=User.EMAIL_DIGEST_TYPES,
        initial=User.EMAIL_DIGEST_TYPE_WEEKLY,
        widget=forms.RadioSelect(),
    )

    class Meta:
        model = User
        fields = [
            "email_digest_type",
        ]


class ExpertiseForm(ModelForm):
    expertise = forms.ChoiceField(
        label="Область",
        required=True,
        choices=EXPERTISE + [("custom", "[добавить своё]")],
    )
    expertise_custom = forms.CharField(
        label="Свой вариант",
        required=False,
        max_length=32
    )
    value = forms.IntegerField(
        label="Скилл",
        min_value=0,
        max_value=100,
        required=True,
        widget=forms.NumberInput(attrs={"type": "range", "step": "1"}),
    )

    class Meta:
        model = UserExpertise
        fields = ["expertise", "value"]

    def clean(self):
        super().clean()
        custom_expertise = self.cleaned_data.get("expertise_custom")
        if custom_expertise:
            self.cleaned_data["expertise"] = custom_expertise

        if not self.cleaned_data["expertise"]:
            raise ValidationError("Name is required")
