from datetime import datetime

import pytz
from django import forms
from django.contrib.postgres.forms import SimpleArrayField
from django.core.exceptions import ValidationError
from slugify import slugify_filename

from common.regexp import EMOJI_RE
from common.url_metadata_parser import parse_url_preview
from posts.models.post import Post
from common.forms import ImageUploadField, ReverseBooleanField
from rooms.models import Room
from tags.models import Tag
from users.models.user import User


class CollectibleTagField(forms.CharField):
    widget = forms.TextInput(attrs={
        "minlength": 5,
        "maxlength": 32,
        "title": "Тег обязан начинаться с emoji, потом пробел, а потом название не длиннее 32 символов"
    })

    def prepare_value(self, value):
        if value:
            tag = Tag.objects.filter(code=value).first()
            if tag:
                return tag.name
        return value

    def to_python(self, value):
        if not value:
            return None

        if " " not in value:
            raise ValidationError("Тег обязан начинаться с emoji, потом идёт пробел, потом название")

        tag_emoji, tag_text = value.split(" ", 1)
        if not EMOJI_RE.match(tag_emoji):
            raise ValidationError("Тег обязан начинаться с emoji")

        if not tag_text:
            raise ValidationError("Название тега не может быть пустым")

        tag_code = slugify_filename(value).lower()
        if not tag_code:
            return None

        tag, _ = Tag.objects.get_or_create(
            code=tag_code,
            defaults=dict(
                name=value,
                group=Tag.GROUP_COLLECTIBLE,
            )
        )
        return tag.code


class AbstractPostForm(forms.ModelForm):
    room = forms.ModelChoiceField(
        label="Комната",
        required=False,
        blank=True,
        queryset=Room.objects.filter(is_visible=True, is_open_for_posting=True).order_by("title").all(),
    )
    collectible_tag_code = CollectibleTagField(
        label="Прикрепить коллекционный тег",
        max_length=32,
        required=False,
    )
    is_visible_in_feeds = ReverseBooleanField(
        label="Пост только для этой комнаты (не отображается на главной)",
        initial=True,
        required=False
    )
    is_public = forms.ChoiceField(
        label="Виден ли в большой интернет?",
        choices=((True, "Публичный пост"), (False, "Только для своих")),
        widget=forms.RadioSelect(attrs={"required": "required"}),
        required=False
    )

    class Meta:
        abstract = True

    def clean_coauthors(self):
        coauthors = self.cleaned_data.get("coauthors")
        if not coauthors:
            return []
        coauthors = [coauthor.replace("@", "", 1) for coauthor in coauthors]

        seen = set()
        duplicated_coauthors = [coauthor for coauthor in coauthors if coauthor in seen or seen.add(coauthor)]
        if duplicated_coauthors:
            raise ValidationError("Пользователи уже соавторы: {}".format(', '.join(duplicated_coauthors)))

        non_existing_coauthors = [coauthor for coauthor in coauthors if not User.objects.filter(slug=coauthor).exists()]
        if non_existing_coauthors:
            raise ValidationError("Несуществующие пользователи: {}".format(', '.join(non_existing_coauthors)))

        return coauthors

    def clean_is_visible_in_feeds(self):
        new_value = self.cleaned_data.get("is_visible_in_feeds")

        if new_value is None:
            return self.instance.is_visible_in_feeds

        if new_value and not self.instance.is_visible_in_feeds:
            raise ValidationError("Нельзя вытаскивать посты обратно из комнат. Только модератор может это сделать")

        return new_value


class IntroForm(forms.ModelForm):
    text = forms.CharField(
        label="Текст интро",
        required=True,
        max_length=500000,
        min_length=600,
        widget=forms.Textarea(
            attrs={
                "minlength": 600,
                "maxlength": 500000,
                "class": "markdown-editor-full",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "text",
        ]


class PostTextForm(AbstractPostForm):
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
    coauthors = SimpleArrayField(
        forms.CharField(max_length=32),
        max_length=10,
        label="Соавторы поста",
        required=False,
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "room",
            "coauthors",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public",
        ]


class PostLinkForm(AbstractPostForm):
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
                "minlength": 350,
                "maxlength": 50000,
                "class": "markdown-editor-full",
                "data-listen": "keyup",
                "placeholder": "Напишите TL;DR чтобы сэкономить другим время."
                               "\n\nКоротко расскажите о чем ссылка, перечислите основные моменты, "
                               "которые вас зацепили, и почему каждый из нас должен пойти её прочитать."
                               "\n\nЕсли тема подразумевает дискуссию — задайте пару вопросов от себя.",
            }
        ),
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "url",
            "room",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public",
        ]

    def clean(self):
        cleaned_data = super().clean()

        parsed_url = parse_url_preview(cleaned_data.get("url"))
        if parsed_url:
            self.instance.metadata = {
                **(self.instance.metadata or {}),
                **dict(parsed_url._asdict())
            }
            self.instance.url = parsed_url.url
            self.instance.image = parsed_url.favicon

        return cleaned_data


class PostQuestionForm(AbstractPostForm):
    title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Вопрос кратко и четко 🤔"}),
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
            "room",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public"
        ]


class PostIdeaForm(AbstractPostForm):
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
            "room",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public",
        ]


class PostEventForm(AbstractPostForm):
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
        initial="Расскажите кратко, что за мероприятие и зачем туда идти: "
                "какой формат, какие активности планируются. "
                "Если это серия ивентов, дайте ссылку на предыдущее или расскажите, как прошло.\n\n"
                "# Для кого мероприятие\n\n"
                "Если мероприятие тематическое (например, киноклуб или хакатон), "
                "расскажите какой минимальный порог вхождения или как нужно подготовиться.\n"
                "Зовёте в бар? Расскажите, чем он знаменит и что в меню.\n\n"
                "# Регистрация\n\n"
                "Если требуется регистрация, то как это сделать, например, "
                "заполнить форму или отметиться в комментариях.\n\n"
                "# Где и когда\n\n"
                "Во сколько запланирован сбор и до скольких примерно продлится мероприятие. "
                "Как найти вход, приложите ссылку на карту или нарисуйте маршрут.\n\n"
                "# Ограничения\n\n"
                "Есть ограничения по вместимости? Не пускают с собаками? Нельзя алкоголь?\n"
                "# Контакты\n\n"
                "Контакты организаторов или чатик, "
                "куда можно присылать вопросы и обсуждать организацию.",
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "class": "markdown-editor-full",
            }
        ),
    )
    coauthors = SimpleArrayField(
        forms.CharField(max_length=32),
        max_length=10,
        label="Соавторы поста",
        required=False,
    )


    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "room",
            "coauthors",
            "collectible_tag_code",
            "is_visible_in_feeds",
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
            **(self.instance.metadata or {}),
            **{
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
        }
        return cleaned_data


class PostProjectForm(AbstractPostForm):
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
    coauthors = SimpleArrayField(
        forms.CharField(max_length=32),
        max_length=10,
        label="Соавторы поста",
        required=False,
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "room",
            "url",
            "image",
            "coauthors",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public",
        ]


class PostBattleForm(AbstractPostForm):
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
            "room",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public",
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


class PostGuideForm(AbstractPostForm):
    title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Клубный Путеводитель: ******",
                "value": "Клубный Путеводитель: ******",
            }
        ),
    )
    text = forms.CharField(
        label="Текст путеводителя",
        required=True,
        max_length=500000,
        initial="Ниже приведён шаблон, который вы можете редактировать как вам будет удобнее.\b\b"
                "Напишите пару предложений введения: чем славится ваш город, как он появился и зачем в него ехать?\n\n"
                "# Карта города\n\n"
                "Обведите на ней все главные места — где центр, где тусить, где жить, где есть, где ходить. "
                "Можете использовать скриншоты с сервиса hoodmaps.com, можете нарисовать свою карту, как удобнее. "
                "Можно даже несколько.\n\n"
                "# Основная информация\n\n"
                "- **Валюта**\n"
                "   - [название, курс и как проще его запомнить]\n"
                "- **Население**\n"
                "   - [количество человек]\n"
                "- **Визы**\n"
                "   - [нужна ли соклубникам виза, паспорт и какой]\n"
                "- **Когда лучше всего приезжать?**\n"
                "   - [месяц или сезон]\n"
                "- **Что обязательно взять с собой?**\n"
                "   - [переходник для розеток, крем от солнца, или просто ничего]\n"
                "- **Как лучше добраться из аэропорта?**\n"
                "   - [можно несколько вариантов, укажите примерные цены]\n"
                "- **Как лучше перемещаться по городу?**\n"
                "   - [взять билет на транспорт или пользоваться такси?]\n"
                "- **Как вызывать такси?**\n"
                "   - [название приложения или телефон]\n"
                "- **Есть ли доставка еды?**\n"
                "   - [название приложения]\n"
                "- **Какую купить туристическую симку?**\n"
                "   - [название и как купить]\n"
                "- **Можно ли везде платить картой?**\n"
                "   - [да, либо сумма денег, которую надо снять]\n"
                "- **Можно ли пить воду из крана?**\n"
                "   - [да/нет/ваш вариант]\n"
                "- **Главные супермаркеты для еды?**\n"
                "   - [названия и чем отличаются]\n"
                "- **Говорят ли люди на улице по-английски?**\n"
                "   - [и как к ним обращаться за помощью]\n"
                "- **Что нужно 100% увидеть и попробовать?**\n"
                "   - [места, люди, явления]\n"
                "- **Чего остерегаться?**\n"
                "   - [места, люди, явления]\n"
                "- **Сколько в среднем стоит 1 шаурма?**\n"
                "   - [в местной валюте]\n\n"
                "# Основной маршрут туриста\n\n"
                "...\n\n"
                "# «Нетуристические» маршруты\n\n"
                "...\n\n"
                "# Где жить?\n\n"
                "...\n\n"
                "# Где и что поесть/выпить?\n\n"
                "...\n\n"
                "# Где затусить вечером?\n\n"
                "...\n\n"
                "# Опционально: где еще стоит побывать? Советы от местных\n\n"
                "...\n\n"
                "# Опционально: что можно купить чтобы увезти с собой\n\n"
                "...\n\n"
                "# Опционально: разговорник и основные фразы\n\n"
                "...\n\n",
        widget=forms.Textarea(
            attrs={
                "maxlength": 500000,
                "class": "markdown-editor-full",
            }
        ),
    )
    coauthors = SimpleArrayField(
        forms.CharField(max_length=32),
        max_length=10,
        label="Соавторы поста",
        required=False,
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "room",
            "coauthors",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public",
        ]


class PostThreadForm(AbstractPostForm):
    title = forms.CharField(
        label="Заголовок",
        required=True,
        max_length=128,
        widget=forms.TextInput(attrs={"placeholder": "Заголовок 🤙"}),
    )
    text = forms.CharField(
        label="Текст треда",
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
    comment_template = forms.CharField(
        label="Шаблон комментария",
        required=True,
        max_length=5000,
        widget=forms.Textarea(
            attrs={
                "maxlength": 5000,
                "class": "markdown-editor-full",
                "placeholder": "Здесь тоже поддерживается и рекомендуется Markdown"
            }
        ),
    )
    coauthors = SimpleArrayField(
        forms.CharField(max_length=32),
        max_length=10,
        label="Соавторы поста",
        required=False,
    )

    class Meta:
        model = Post
        fields = [
            "title",
            "text",
            "comment_template",
            "room",
            "coauthors",
            "collectible_tag_code",
            "is_visible_in_feeds",
            "is_public",
        ]


POST_TYPE_MAP = {
    Post.TYPE_INTRO: IntroForm,
    Post.TYPE_POST: PostTextForm,
    Post.TYPE_LINK: PostLinkForm,
    Post.TYPE_QUESTION: PostQuestionForm,
    Post.TYPE_IDEA: PostIdeaForm,
    Post.TYPE_PROJECT: PostProjectForm,
    Post.TYPE_BATTLE: PostBattleForm,
    Post.TYPE_EVENT: PostEventForm,
    Post.TYPE_GUIDE: PostGuideForm,
    Post.TYPE_THREAD: PostThreadForm,
}
