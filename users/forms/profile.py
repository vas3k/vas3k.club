from django import forms
from django.forms import ModelForm

from common.data.countries import COUNTRIES
from posts.models.post import Post
from users.models.user import User
from common.forms import ImageUploadField


class ProfileEditForm(ModelForm):
    avatar = ImageUploadField(
        label="Аватар",
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
    profile_publicity_level = forms.ChoiceField(
        label="Уровень публичности профиля",
        choices=User.PUBLICITY_LEVELS,
        initial=User.PUBLICITY_LEVEL_NORMAL,
        widget=forms.RadioSelect(),
        required=False,
    )

    class Meta:
        model = User
        fields = [
            "avatar",
            "company",
            "position",
            "city",
            "country",
            "bio",
            "profile_publicity_level",
        ]

    def clean_profile_publicity_level(self):
        new_value = self.cleaned_data["profile_publicity_level"]
        old_value = self.instance.profile_publicity_level

        # update intro post visibility settings
        if new_value != old_value:
            if new_value == User.PUBLICITY_LEVEL_PUBLIC:
                Post.objects.filter(author=self.instance, type=Post.TYPE_INTRO).update(is_public=True)
            else:
                Post.objects.filter(author=self.instance, type=Post.TYPE_INTRO).update(is_public=False)

        return new_value


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
