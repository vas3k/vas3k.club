from django import forms

from common.url_metadata_parser import parse_url_preview
from posts.models import Topic, Post
from utils.forms import ImageUploadField


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


class PostPainForm(PostForm):
    title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Кратко суть боли 😭"}),
    )
    text = forms.CharField(
        label="Развернутое описание",
        required=True,
        max_length=500000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "class": "markdown-editor-full",
                "placeholder": "Поделитесь своей болью в подробностях. "
                               "\n\nРасскажите примеры ситуаций, когда проблема возникает. "
                               "Приведите пример того, как вы решаете проблему сейчас."
                               "\n\nВ конце укажите сколько вы были бы готовы платить за продукт, "
                               "который смог бы решить эту проблему. Единоразово, подпиской или процент?",
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
        convert_format=None
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


POST_TYPE_MAP = {
    Post.TYPE_POST: PostTextForm,
    Post.TYPE_LINK: PostLinkForm,
    Post.TYPE_QUESTION: PostQuestionForm,
    Post.TYPE_PAIN: PostPainForm,
    Post.TYPE_PROJECT: PostProjectForm,
}