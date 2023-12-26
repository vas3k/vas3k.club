import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from common.data.countries import COUNTRIES
from users.models.user import User
from common.forms import ImageUploadField


class UserInitialIntroForm(ModelForm):
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
        label="Как вас зовут",
        required=True,
        max_length=128
    )
    email = forms.EmailField(
        label="E-mail",
        required=True
    )
    avatar = ImageUploadField(
        label="Аватар или фото",
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
        label="Контакты, соцсети и краткое био",
        required=True,
        max_length=1024,
        widget=forms.Textarea(attrs={"maxlength": 1024}),
    )
    company = forms.CharField(
        label="Компания",
        required=True,
        max_length=128
    )
    position = forms.CharField(
        label="Должность или что вы делаете",
        required=True,
        max_length=128
    )
    intro = forms.CharField(
        label="#intro",
        required=True,
        widget=forms.Textarea(
            attrs={
                "maxlength": 10000,
                "minlength": 600,
                "placeholder": "Расскажите Клубу о себе...",
            }
        ),
    )
    email_digest_type = forms.ChoiceField(
        label="Подписка на дайджест",
        required=True,
        choices=User.EMAIL_DIGEST_TYPES,
        initial=User.EMAIL_DIGEST_TYPE_WEEKLY,
        widget=forms.RadioSelect(),
    )
    privacy_policy_accepted = forms.BooleanField(
        label="Даю согласие на обработку своих персональных данных", required=True
    )

    class Meta:
        model = User
        fields = [
            "slug",
            "full_name",
            "email",
            "avatar",
            "company",
            "position",
            "city",
            "country",
            "bio",
            "email_digest_type",
        ]

    def clean_slug(self):
        slug = self.cleaned_data["slug"]
        slug = str(slug).strip()

        if slug:
            if not re.match(r"^[a-zA-Z0-9-_]+$", slug):
                raise ValidationError("В нике использованы недопустимые знаки")

            is_exists = (
                User.objects.filter(slug__iexact=slug)
                    .exclude(id=self.instance.id if self.instance else None)
                    .exists()
            )

            if not is_exists:
                return slug

        raise ValidationError("Пользователь с таким ником уже существует. Выберите другой")
