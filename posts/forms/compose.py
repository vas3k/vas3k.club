from django import forms

from common.url_metadata_parser import parse_url_preview
from posts.models import Topic, Post
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
        initial=True,
        required=False
    )
    is_visible = forms.BooleanField(
        label="Виден ли пост вообще?",
        initial=False,
        required=False
    )
    is_visible_on_main_page = forms.BooleanField(
        label="Видел ли пост на главной странице?",
        initial=True,
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
                "placeholder": "Дорогой Мартин Алексеевич..."
            }
        ),
    )

    class Meta:
        model = Post
        fields = ["title", "text", "topic", "is_visible", "is_public"]


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
        widget=forms.Textarea(
            attrs={
                "maxlength": 50000,
                "class": "markdown-editor-full",
                "placeholder": "Напишите TL;DR чтобы сэкономить другим время."
                               "\n\nКоротко расскажите о чем ссылка и почему все должны её прочитать. ",
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
            "is_visible",
            "is_public"
        ]

    def clean(self):
        cleaned_data = super().clean()

        parsed_url = parse_url_preview(cleaned_data["url"])
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
            "is_visible",
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
            "is_visible",
            "is_public"
        ]


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
        initial="🤗 Расскажите здесь все подробности о вашем проекте.\n\n "
                "Этот текст можете смело удалять. Он здесь лишь для того, чтобы помочь вам с проблемой чистого листа "
                "и задать базовую структуру. Главное — чтобы это было полезно. "
                "Можете добавлять или изменять вопросы, чтобы они лучше описывали ваш случай.\n\n"
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
                "class": "markdown-editor-full",
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
            "is_visible",
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
            "is_visible",
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
}
