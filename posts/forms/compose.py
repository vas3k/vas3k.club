from datetime import datetime

import pytz
from django import forms
from django.core.exceptions import ValidationError

from common.url_metadata_parser import parse_url_preview
from posts.models.post import Post
from posts.models.topics import Topic
from common.forms import ImageUploadField


class PostForm(forms.ModelForm):
    topic = forms.ModelChoiceField(
        label="Комната",
        required=False,
        empty_label="Для всех",
        queryset=Topic.objects.filter(is_visible=True).all(),
    )
    is_public = forms.BooleanField(
        label="Виден ли в большой интернет?",
        initial=False,
        required=False
    )

    class Meta:
        abstract = True

    def clean_topic(self):
        topic = self.cleaned_data["topic"]

        if topic and not topic.is_visible_on_main_page:
            # topic settings are more important
            self.instance.is_visible_on_main_page = False

        return topic


class PostTextForm(PostForm):
    title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Заголовок 🤙"}),
    )
    text = forms.CharField(
        label="Текст поста",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "class": "markdown-editor-full",
                "placeholder": "Дорогой Мартин Алексеевич…"
            }
        ),
    )

    class Meta:
        model = Post
        fields = ["title", "text", "topic", "is_public"]


class PostLinkForm(PostForm):
    url = forms.URLField(
        label="Ссылка",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Вставьте ссылку сюда 🤏"}),
    )
    title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Заголовок ссылки"}),
    )
    text = forms.CharField(
        label="TL;DR",
        required=True,
        max_length=50000,
        min_length=350,
        widget=forms.Textarea(
            attrs={
                "minlength": 350,
                "maxlength": 50000,
                "class": "markdown-editor-full",
                "data-listen": "keyup",
                "placeholder": "Напишите TL;DR чтобы сэкономить другим время."
                               "\n\nКоротко расскажите о чем ссылка, перечислите основные моменты, "
                               "которые вас зацепили, и почему каждый из нас должен пойти её прочитать.",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "url",
            "topic",
            "is_public"
        ]

    def clean(self):
        cleaned_data = super().clean()

        parsed_url = parse_url_preview(cleaned_data.get("url"))
        if parsed_url:
            self.instance.metadata = dict(parsed_url._asdict())
            self.instance.url = parsed_url.url
            self.instance.image = parsed_url.favicon

        return cleaned_data


class PostQuestionForm(PostForm):
    title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Вопрос коротко 🤔"}),
    )
    text = forms.CharField(
        label="Развернутая версия",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "class": "markdown-editor-full",
                "placeholder": "Больше подробностей — быстрее кто-нибудь сможет вам помочь. "
                               "Но и перебарщивать не стоит. "
                               "\n\nОсобенно полезно будет узнать какие решения "
                               "вы уже попробовали и почему они не подошли.",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "topic",
            "is_public"
        ]


class PostIdeaForm(PostForm):
    title = forms.CharField(
        label="Суть идеи",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Кратко суть идеи 🤔"}),
    )
    text = forms.CharField(
        label="Развернутое описание",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "class": "markdown-editor-full",
                "placeholder": "Поделитесь подробностями, предысторией и проблемами, которые легли в основу идеи. "
                               "Приведите примеры похожих продуктов...",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "topic",
            "is_public"
        ]


class PostEventForm(PostForm):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance and instance.metadata:
            kwargs.update(initial={
                "event_day": instance.metadata.get("event", {}).get("day") or datetime.utcnow().day,
                "event_month": instance.metadata.get("event", {}).get("month") or datetime.utcnow().month,
                "event_time": instance.metadata.get("event", {}).get("time") or "00:00",
                "event_timezone": instance.metadata.get("event", {}).get("timezone") or "UTC",
                "event_location": instance.metadata.get("event", {}).get("location") or "",
            })
        super().__init__(*args, **kwargs)

    title = forms.CharField(
        label="Название события",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Название и дата события 📅"}),
    )
    event_day = forms.ChoiceField(
        label="День",
        required=True,
        initial=lambda: datetime.utcnow().day,
        choices=[(i, i) for i in range(1, 32)],
    )
    event_month = forms.ChoiceField(
        label="Месяц",
        required=True,
        initial=lambda: datetime.utcnow().month,
        choices=[
            (1, "января"),
            (2, "февраля"),
            (3, "марта"),
            (4, "апреля"),
            (5, "мая"),
            (6, "июня"),
            (7, "июля"),
            (8, "августа"),
            (9, "сентября"),
            (10, "октября"),
            (11, "ноября"),
            (12, "декабря"),
        ]
    )
    event_time = forms.TimeField(
        label="Время",
        required=True,
        widget=forms.TimeInput(attrs={"type": "time", "value": "10:00"}),
    )
    event_timezone = forms.ChoiceField(
        label="Таймзона",
        required=True,
        choices=[
            ("Europe/Moscow", "по Москве"),
            ("UTC", "UTC"),
        ]
    )
    event_location = forms.CharField(
        label="Локейшен",
        required=True,
        max_length=140,
        widget=forms.TextInput(attrs={"placeholder": "📍 Адрес или ссылка"}),
    )
    text = forms.CharField(
        label="Развернутое описание",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "class": "markdown-editor-full",
                "placeholder": "Расскажите что, где и когда произойдёт. "
                               "Не забудьте оставить контакты для связи с организаторами "
                               "и приложить все необходимые ссылочки.",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "topic",
            "is_public"
        ]

    def clean(self):
        cleaned_data = super().clean()

        # validate event date
        try:
            now = datetime.utcnow()
            year = now.year if int(cleaned_data["event_month"]) >= now.year else now.year + 1
            datetime(
                year=year,
                month=int(cleaned_data["event_month"]),
                day=int(cleaned_data["event_day"]),
                hour=cleaned_data["event_time"].hour,
                minute=cleaned_data["event_time"].minute,
                second=cleaned_data["event_time"].second,
            )
        except (KeyError, ValueError):
            raise ValidationError({"event_day": "Несуществующая дата"})

        self.instance.metadata = {
            "event": {
                "day": cleaned_data["event_day"],
                "month": cleaned_data["event_month"],
                "time": str(cleaned_data["event_time"]),
                "timezone": cleaned_data["event_timezone"],
                "utc_offset": datetime.now(pytz.timezone(cleaned_data["event_timezone"]))
                .utcoffset().total_seconds() // 60,
                "location": cleaned_data["event_location"],
            }
        }
        return cleaned_data


class PostProjectForm(PostForm):
    title = forms.CharField(
        label="Название проекта",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Название проекта 🏗"}),
    )
    url = forms.URLField(
        label="Ссылка на страницу проекта 👇",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "https://"}),
    )
    image = ImageUploadField(
        label="Скриншот или иконка",
        required=True,
        resize=(1024, 1024),
    )
    text = forms.CharField(
        label="Описание",
        required=True,
        min_length=1500,
        initial="🤗 Расскажите нам все инсайды о вашем проекте.\n\n "
                "Ниже мы накидали список популярных вопросов, на которые обычно всем интересно услышать ответы. "
                "Он здесь для того, чтобы помочь вам с проблемой чистого листа и задать базовую структуру. "
                "Не нужно понимать его буквально. Главное — чтобы другим было полезно читать ваш опыт.\n\n"
                "⚠️ И еще раз: короткие односложные ответы на вопросы не считаются хорошим рассказом о проекте "
                "и будут расценены модераторами как спам. Нам интересен именно ваш опыт и истории, "
                "а не технические ответы на вопросы!\n\n"
                "### Расскажите о себе и сути проекта?\n\n\n\n"
                "### Как появилась идея? Что вдохновило?\n\n\n\n"
                "### Что вошло в прототип и сколько времени на него было потрачено?\n\n\n\n"
                "### Какой технологический стек вы использовали? Почему?\n\n\n\n"
                "### Как вы запускались и искали первых пользователей?\n\n\n\n"
                "### С какими самыми неожиданными трудностями пришлось столкнуться?\n\n\n\n"
                "### Сколько потратили и заработали? Есть идеи как это можно монетизировать?\n\n\n\n"
                "### Какие планы на будущее?\n\n\n\n"
                "### Нужны ли какие-то советы или помощь Клуба?\n\n\n\n"
                "### Какой совет вы бы сами могли дать идущим по вашим стопам?\n\n",
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "minlength": 1500,
                "class": "markdown-editor-full",
                "data-listen": "keyup",
                "placeholder": "Расскажите подробности о вашем проекте!"
                               "\n- В чем его суть и как он помогает людям?"
                               "\n- Как появилась идея?"
                               "\n- Какой технический стек вы использовали?"
                               "\n- С какими самыми неожиданными трудностями вы столкнулись?"
                               "\n- Сколько в итоге потратили и заработали?"
                               "\n- Нужны ли какие-то советы или помошь Клуба?"
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "topic",
            "url",
            "image",
            "is_public"
        ]


class PostBattleForm(PostForm):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        if instance and instance.metadata:
            kwargs.update(initial={
                "side_a": instance.metadata.get("battle", {}).get("sides", {}).get("a", {}).get("name") or "",
                "side_b": instance.metadata.get("battle", {}).get("sides", {}).get("b", {}).get("name") or "",
            })
        super().__init__(*args, **kwargs)

    side_a = forms.CharField(
        label="Одна сторона",
        required=True,
        max_length=64,
    )
    side_b = forms.CharField(
        label="Вторая сторона",
        required=True,
        max_length=64,
    )
    text = forms.CharField(
        label="Суть",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 5000,
                "class": "markdown-editor-full",
                "placeholder": "Не все логические дилеммы очевидны с первого взгляда. "
                               "Дайте нам немного контекста.\n\n"
                               "Старайтесь не давать субъективных оценок. "
                               "Ваше мнение может повлиять на участников и исказить результаты. "
                               "Лучше напишите его первым комментарием после публикации батла.",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "text",
            "topic",
            "is_public"
        ]

    def clean(self):
        cleaned_data = super().clean()
        self.instance.is_public = True  # FIXME: dirty hardcode
        self.instance.metadata = {
            "battle": {
                "sides": {
                    "a": {"name": cleaned_data["side_a"]},
                    "b": {"name": cleaned_data["side_b"]},
                }
            }
        }
        self.instance.title = f"{cleaned_data['side_a']} или {cleaned_data['side_b']}"
        cleaned_data["title"] = self.instance.title
        return cleaned_data


POST_TYPE_MAP = {
    Post.TYPE_POST: PostTextForm,
    Post.TYPE_LINK: PostLinkForm,
    Post.TYPE_QUESTION: PostQuestionForm,
    Post.TYPE_IDEA: PostIdeaForm,
    Post.TYPE_PROJECT: PostProjectForm,
    Post.TYPE_BATTLE: PostBattleForm,
    Post.TYPE_EVENT: PostEventForm,
}
