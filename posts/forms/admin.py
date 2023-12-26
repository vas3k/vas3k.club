from django import forms

from common.data.labels import LABELS
from posts.models.post import Post


class PostCuratorForm(forms.Form):
    change_type = forms.ChoiceField(
        label="Сменить тип поста",
        choices=[(None, "---")] + Post.TYPES,
        required=False,
    )

    new_label = forms.ChoiceField(
        label="Выдать лейбл",
        choices=[(None, "---")] + [(key, value.get("title")) for key, value in LABELS.items()],
        required=False,
    )

    remove_label = forms.BooleanField(
        label="Удалить текуший лейбл",
        required=False
    )

    add_pin = forms.BooleanField(
        label="Запинить",
        required=False
    )

    pin_days = forms.IntegerField(
        label="На сколько дней пин?",
        initial=1,
        required=False
    )

    remove_pin = forms.BooleanField(
        label="Отпинить обратно",
        required=False
    )

    move_up = forms.BooleanField(
        label="Подбросить на главной",
        required=False
    )

    move_down = forms.BooleanField(
        label="Опустить на главной",
        required=False
    )

    shadow_ban = forms.BooleanField(
        label="Шадоу бан (редко!)",
        required=False,
    )

    hide_from_feeds = forms.BooleanField(
        label="Скрыть с главной",
        required=False,
    )

    show_in_feeds = forms.BooleanField(
        label="Вернуть на главную (или вытащить из комнаты)",
        required=False,
    )

    re_ping_collectible_tag_owners = forms.BooleanField(
        label="Перепингануть подписчиков коллективного тега",
        required=False,
    )


class PostAdminForm(PostCuratorForm):
    toggle_is_commentable = forms.BooleanField(
        label="Закрыть комменты (повторный клик переоткроет заново)",
        required=False,
    )

    transfer_ownership = forms.CharField(
        label="Передать владение постом другому юзернейму",
        required=False,
    )

    refresh_linked = forms.BooleanField(
        label="Обновить связанные посты",
        required=False,
    )


class PostAnnounceForm(forms.Form):
    text = forms.CharField(
        label="Текст анонса",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
            }
        ),
    )
    image = forms.CharField(
        label="Картинка",
        required=False,
    )
    with_image = forms.BooleanField(
        label="Постим с картинкой?",
        required=False,
        initial=True,
    )
