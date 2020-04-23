import re

from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from common.data.achievements import ACHIEVEMENTS
from common.data.countries import COUNTRIES
from common.data.expertise import EXPERTISE
from common.data.hats import HATS
from utils.forms import ImageUploadField
from users.models import User, UserExpertise


class UserIntroForm(ModelForm):
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
        label="Имя",
        required=True,
        max_length=128
    )
    email = forms.EmailField(
        label="E-mail",
        required=True
    )
    avatar = ImageUploadField(
        label="Аватар",
        required=False,
        resize=(512, 512)
    )
    city = forms.CharField(
        label="Город",
        required=True,
        max_length=120
    )
    country = forms.ChoiceField(
        label="Страна",
        choices=COUNTRIES,
        required=True
    )
    bio = forms.CharField(
        label="Краткая строчка о себе",
        required=False,
        max_length=512,
        widget=forms.Textarea(attrs={"maxlength": 512}),
    )
    company = forms.CharField(
        label="Компания",
        required=False,
        max_length=128
    )
    position = forms.CharField(
        label="Должность",
        required=True,
        max_length=128
    )
    intro = forms.CharField(
        label="#intro",
        required=True,
        widget=forms.Textarea(
            attrs={
                "maxlength": 5000,
                "class": "markdown-editor-invisible",
                "placeholder": "Писать о себе всегда сложно, так что вот какой план:"
                               "\n\n- Расскажите чем вы занимаетесь и где сейчас работаете?"
                               "\n- Из какого вы города и как там оказались?"
                               "\n- Что делаете в свободное от работы время?"
                               "\n- Может у вас есть странная привычка или хобби?"
                               "\n- О чем вы мечтаете?"
                               "\n- Какой из последних постов Вастрика вам понравился больше всего?",
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


class UserEditForm(ModelForm):
    full_name = forms.CharField(
        label="Имя",
        required=True,
        max_length=128
    )
    avatar = ImageUploadField(
        label="Аватар",
        required=False,
        resize=(512, 512)
    )
    city = forms.CharField(
        label="Город",
        required=True,
        max_length=120
    )
    country = forms.ChoiceField(
        label="Страна",
        choices=COUNTRIES,
        required=True
    )
    bio = forms.CharField(
        label="Краткая строчка о себе",
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
        label="Должность",
        required=True,
        max_length=128
    )
    email_digest_type = forms.ChoiceField(
        label="Подписка на дайджест",
        required=True,
        choices=User.EMAIL_DIGEST_TYPES,
        initial=User.EMAIL_DIGEST_TYPE_WEEKLY,
        widget=forms.RadioSelect(),
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
            "email_digest_type",
        ]


class ExpertiseForm(ModelForm):
    expertise = forms.ChoiceField(
        label="Область",
        required=False,
        choices=EXPERTISE + [("custom", "[добавить своё]")],
        widget=forms.Select(
            attrs={"onchange": "onExpertiseSelectionChanged(event)"}  # wow, so bad
        ),
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
        resize=(256, 256)
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

    add_achievement = forms.BooleanField(
        label="Выдать новую ачивку",
        required=False
    )
    new_achievement = forms.ChoiceField(
        label="Выбрать",
        choices=[(None, "---")] + [(key, value.get("title")) for key, value in ACHIEVEMENTS.items()],
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
