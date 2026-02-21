import logging
import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django_q.tasks import async_task
from typing import TypedDict, ClassVar, Literal
from telegram import ParseMode

from notifications.telegram.common import send_telegram_message, Chat, CLUB_CHAT
from users.models.user import User


log = logging.getLogger(__name__)

HOUR_SEC = 60 * 60
DAY_SEC = 24 * HOUR_SEC
ANTIC_TYPE = Literal["common", "private", "bottom_link"]


class _Message(TypedDict):
    title: str
    message: str


class _MessageTemplate(TypedDict):
    title: str
    message_texts: list[str]


class _Link(TypedDict):
    icon: str
    label: str


class AnticHandlerBase():
    name: ClassVar[str]
    type: ANTIC_TYPE
    date: tuple[int, int]
    duration: int  # days
    link: _Link

    global_timeout: ClassVar[int] = 0  # for common chat notifications

    already_send_errors: _MessageTemplate = {
        "title": "Повторная отправка! 🧐",
        "message_texts": [
            "У нас ощущение, что вы уже отправляли этому пользователю 🪛",
        ],
    }
    its_you_errors: _MessageTemplate = {
        "title": "Всё пошло не так! 🧐",
        "message_texts": [
            "Ну и дела!\nПохоже, вы пытаетесь отправить это самому себе, мы так не умеем.",
        ],
    }
    success_messages: _MessageTemplate = {
        "title": "Ура, доставлено 🌟",
        "message_texts": [
            "Всё успешно отправлено, сценарий Seele выполнен в точности 📱",
        ],}

    # === inner things

    user_timeout: ClassVar[int] = 30

    not_today_errors: _MessageTemplate = {
        "title": "Ой, это не должно произойти сегодня 📆",
        "message_texts": [
            "Подожди чуть-чуть и попробуй ещё раз в нужное время 👁️👁️",
            "А сегодня можешь почитать пост:\n\n https://vas3k.club/post/random/",
            "Кажется, все даты решили перепутаться 🤖"
        ],
    }
    global_cooldown_errors: _MessageTemplate = {
        "title": "Ой! Кто-то это недавно уже использовал 🥺",
        "message_texts": [
            "Кто первый встал - того и кнопка 🛴",
            "Следующий раз нужно быть быстрее 🍎",
            "Но всегда можно пойти и пообщаться в [Баре](https://vas3k.club/room/bar/chat/)",
        ],
    }
    user_cooldown_errors: _MessageTemplate = {
        "title": "Ой! Вы слишком часто нажимали на кнопочку 🧐",
        "message_texts": [
            "Нужно чуть-чуть подождать, это пройдёт 🕓",
            "А пока можно выпить же чаю и съесть ещё этих мягких французских булок.",
            "Мы бы и рады помочь, но это же кнопочка, мы её не можем контролировать 😳",
        ]
    }
    no_telegram_errors: _MessageTemplate = {
        "title": "Мы не смогли доставить посылку 😮",
        "message_texts": [
            "Получатель не привязал телеграм. Мы так не играем!",
            "Получатель предпочёл скрыть от нас телеграм. Вот и пусть сидит без уведомляшек!",
            "Возможно, получатель скрылся от мира. По крайней мере, мы не нашли его телеграм.",
        ],
    }
    default_errors: _MessageTemplate = {
        "title": "Что-то произошло, но мы не знаем, что 🐞",
        "message": [
            "О нет, всё поломалось. Мы к такому не готовились 😳",
            "Ой! Вы что-то нажали и всё сломалось 🌀",
            "Планировалось сделать всё как нужно, но получилось как всегда 🔧",
            "Попробовали всё сделать хорошо. Но не получилось 🍿",
        ],
    }

    @staticmethod
    def _make_message(template: _MessageTemplate) -> _Message:
        return _Message(
            title=template["title"],
            message=random.choice(template["message_texts"]),
        )

    @classmethod
    def _is_today(cls) -> bool:
        antic_start = date(2000, *cls.date)
        antic_end = antic_start + timedelta(days=cls.duration)
        year_td = relativedelta(years=1)
        today = date.today().replace(year=2000)
        return (
            antic_start <= today < antic_end
            or (antic_start - year_td) <= today < (antic_end - year_td)  # new year
        )

    @classmethod
    def _is_global_cooldown_active(cls) -> bool | None:
        if cls.global_timeout:
            return cache.get(f"fun:antic:{cls.name}")
        return None

    @classmethod
    def _is_user_cooldown_active(cls, sender: User) -> bool | None:
        return cache.get(f"fun:antic:{cls.name}:{sender.id}")

    @classmethod
    def _is_already_sent(cls, sender: User, recipient: User) -> bool | None:
        return cache.get(f"fun:antic:{cls.name}:{sender.id}:{recipient.id}")

    @classmethod
    def _set_global_cooldown(cls) -> None:
        if cls.global_timeout:
            cache.set(f"fun:antic:{cls.name}", True, timeout=cls.global_timeout)

    @classmethod
    def _set_user_cooldown(cls, sender: User) -> None:
        cache.set(f"fun:antic:{cls.name}:{sender.id}", True, timeout=cls.user_timeout)

    @classmethod
    def _set_already_send(cls, sender: User, recipient: User | None) -> None:
        if recipient:
            cache.set(
                f"fun:antic:{cls.name}:{sender.id}:{recipient.id}",
                True,
                timeout=cls.duration * DAY_SEC,
            )

    # === main methods

    @classmethod
    def is_displayable(cls, sender: User, recipient: User | None) -> bool:
        if (
            not cls._is_today()
            or cls._is_global_cooldown_active()
            or cls._is_user_cooldown_active(sender)
        ):
            return False

        if recipient and (
            sender.id == recipient.id
            or not recipient.telegram_id
            or cls._is_already_sent(sender, recipient)
        ):
            return False

        return True

    @staticmethod
    def send_message(text: str, to_chat: Chat = CLUB_CHAT) -> None:
        async_task(
            send_telegram_message,
            chat=to_chat,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )

    @classmethod
    def handle(cls, sender: User, recipient: User | None = None) -> tuple[bool, _Message]:
        if not cls._is_today():
            return False, cls._make_message(cls.not_today_errors)
        if cls._is_global_cooldown_active():
            return False, cls._make_message(cls.global_cooldown_errors)
        if cls._is_user_cooldown_active(sender):
            return False, cls._make_message(cls.user_cooldown_errors)

        if recipient:
            if sender.id == recipient.id:
                return False, cls._make_message(cls.its_you_errors)
            if not recipient.telegram_id:
                return False, cls._make_message(cls.no_telegram_errors)
            if cls._is_already_sent(sender, recipient):
                return False, cls._make_message(cls.already_send_errors)

        try:
            cls.handler(sender, recipient)
        except Exception as exc:
            log.warning(f"Error handling antic: {exc}")
            return False, cls._make_message(cls.default_errors)

        cls._set_global_cooldown()
        cls._set_user_cooldown(sender)
        cls._set_already_send(sender, recipient)

        return True, cls._make_message(cls.success_messages)

    @classmethod
    def handler(cls, sender: User, recipient: User | None) -> tuple[bool, _Message]:
        raise NotImplementedError("No ")


def new_year(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Поздравление улетело поздравлять ❄️",
        message=random.choice(
            [
                "А все причастные поздравляют тебя в ответ! 🎄",
                "И тебя тоже с праздником! 🎆",
                "Клубни получили новогоднее поздравление 🎁",
                "Новый год начал обрабатываться 🌟",
                "Теперь самое время отвлечься от экранов и пойти праздновать 🥂",
                "Хо-хо-хо, Новый год стал новогоднее 🎅",
            ]
        ),
    )


def new_year_private(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Поздравление улетело клубню 📨",
        message=random.choice(
            [
                "Адресат уже мысленно чокается с тобой 🥂",
                "Кстати, оливье, правильно приготовленный, на следующий день вкуснее, чем в"
                " день приготовления. Ну, просто напоминаем.",
                "Но вот где же носит того седого старика, который что-то кому-то достаёт из"
                " рюкзака?",
                "Он стал чуточку счастливее 🎁",
                "Он там по ту сторону экрана улыбается, кстати (возможно, виноват глинтвейн).",
                "Праздник аккуратно передан точно в руки 🎄",
                "Слышишь? Куранты всё ближе 🔔",
                "Теперь у адресата официально праздничное настроение 📜",
            ]
        ),
    )


def valentine_common(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Вы публично рассказали свою любовь ☺️",
        message=random.choice(
            [
                "Клубни растроганы и слегка смущены 🌹",
                "Любовь синхронизирована 💞",
                "Причастные радостно получили сердечки 💖",
                "Сегодня разрешено быть сентиментальным 💝",
                "Эмоции доставлены в целости и нежности ❤",
            ]
        ),
    )


def valentine(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Шоколадка передана 🍫",
        message=random.choice(
            [
                "Теперь адресат знает, что вы его цените 💑🏻",
                "Правильно, любовь нужно дарить 💞",
                "Много любви не бывает 💕",
                "Не забудь, что тебя тоже любят! 🩷",
            ]
        ),
    )


def valentine_anonymous(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Валентинка отправлена 💌",
        message=random.choice(
            [
                "В мире стало чуть больше любви. И чуть больше неизвестности 🥷",
                "И мы передали её абсолютно анонимно 🤿",
                "И пусть адресат теперь гадает, от кого она 💟",
                "Но получатель не узнает, кто её отправил 🕵️🏻‍️",
            ]
        ),
    )


def leap_day(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Вы зафиксировали временной парадокс 👀",
        message=random.choice(
            [
                "Пусть все его наблюдают! 👓",
                "Следующий раз такое будет нескоро 🕖",
                "Этим вы сломали все наши даты 🔐",
            ]
        ),
    )


def fools_day(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Анекдот улетел куда надо 🤡",
        message=random.choice(
            [
                "Беги тоже его скорее читай 🎠",
                "Можно расслабиться и просто подурачиться 🪅",
                "И на что мы только тратим электроэнергию...",
                "А там армяне в нарды играют ♟️",
                "А куда надо ему как раз! 🎩",
                "Прилетел туда и сгорел 🐻",
                "Но есть один нюанс ☝",
            ]
        ),
    )


def cosmonautics_day(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Поздравление улетело 🚀",
        message=random.choice(
            [
                "Бип-бип-бип-бип, поздравление отправлено в чат 🛰️",
                "Сигнал совершил круг вокруг всей Земли, чтобы прилететь в чат 🌍",
                "Следующая остановка - Марс 👨‍🚀",
            ]
        ),
    )


def club_birthday(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Ура, Клуб поздравлен 🎉",
        message=random.choice(
            [
                "Все червячки отправились на праздник 🪱",
                "Держи тортик 🍰",
                "Еее, празднуем! 🎆",
                "Задуваем свечи и загадываем долгую счастливую жизнь (для Клуба) 🎂",
                "Тусим-тусим, праздник! 🎊",
            ]
        ),
    )


def summer_solstice(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="На сегодняшнюю дату пролит свет ☀",
        message=random.choice(
            [
                "Несите дрова и медвежью шкуру! 🔥",
                "И да, уже почти прошёл июнь 🌞",
                "Кстати, держи венок, сегодня ты - Королева мая 🌼🌼🌼🌼",
            ]
        ),
    )


def friends_day(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Клубни поздравлены и дружелюбны 🧑‍🤝‍🧑",
        message=random.choice(
            [
                "А ещё дружба - не только станция метро в Ереване, держим в курсе 🍕",
                "Дружба, мир, жвачка! 🧙🏻‍♂️",
                "Мы все теперь друзяшки! 🤠",
            ]
        ),
    )


def friends_day_private(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Друг поздравлен 💅",
        message=random.choice(
            [
                "Дружба - это весело! Давайте дружить все?",
                "Кстати, глянь, где лежат [все друзяшки](https://vas3k.club/user/me/friends/).",
                "Теперь он знает, что он ваш друг. Наверное.",
                "Ты можешь поздравить и остальных своих друзей.\nПогоди, ты что, плачешь?",
            ]
        ),
    )


def cats_day(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Чат успешно назван котятами 🐱",
        message=random.choice(
            [
                "Все массово мурлыкают 😻",
                "И ты тоже котик 🐈",
                "Мяв. Мяв. Мур 🐈",
            ]
        ),
    )


def cats_day_private(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Адресат получил мявобщение 😼",
        message=random.choice(
            [
                "А глянь, какой ещё в Клубе есть [котик](https://vas3k.club/user/me/)!",
                "Мявмяв мяяв мур мявмяв. Мяв.\n\nВпрочем, забейте, это был _КОТОМБУР_.",
                "Надеемся, у него нет собаки. А то придётся лезть на дерево 🙀",
                "Ну вот, скатываемся. Точнее, _СКОТЫВАЕМСЯ_ 🐈",
                "Теперь вам придётся его гладить и кормить несколько раз в день 🐟",
                "Теперь он котик. И ты котик.",
            ]
        ),
    )


def testers_day(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Баги ÑƒÑ�Ð¿ÐµÑˆÐ½Ð¾ созданы 🪲",
        message=random.choice(
            [
                "[На главную](/user/me/edit/account/)",
                "{% MESSAGE_DETAILS_TEXT %}",
                "А сюда [.button.button-red НЕ НАЖИМАТЬ](/label/wow/)",
                "Было оповещено {receiver_count} человек.",
                "ЭТО СООБЩЕНИЕ ПОПАЛО СЮДА ПО НЕДОСМОТРУ РЕВЬЮЕРОВ ХЕХЕХЕ 🚨",
                '<a href="https://vas3k.club/">Вернуться на главную</a>',
            ]
        ),
    )


def halloween(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Хехехе, чат напуган 🎃",
        message=random.choice(
            [
                "**БУУУУ** 👻\n\nИ вы теперь напуганы.",
                "А вы задумывались, почему тыквенный спас ассоциируют со всякими пугалками? 🤔",
                "Но не переживайте, они всё понимают 🍁",
            ]
        ),
    )


def coffees_day(sender: User, recipient: User | None = None) -> tuple[bool, _Message]:

    return True, _Message(
        title="Кофе в процессе доставки 🐌",
        message=random.choice(
            [
                "Чат можно было и пожалеть, там и так уже все от кофетрясутся! ☕",
                "Самое время лечь поспать 😴",
                "Теперь они немного более кофеинезированы ☕",
            ]
        ),
    )


def western_christmas(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Чат поздравлен 💫",
        message=random.choice(
            [
                "Заваривайте чашечку глинтвейна и залетайте с ним в"
                " [Бар](https://vas3k.club/room/bar/chat/) 🥃",
                "И тебя с праздником! 🎄",
                "Он родился. А что произошло дальше, мы с вами сейчас и узнаем 🐙",
            ]
        ),
    )


def western_christmas_private(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:

    return True, _Message(
        title="Поздравление улетело 💫",
        message=random.choice(
            [
                "А что это ещё летит? А, это вайб на подлёте! Вот он: ✨✨✨",
                "Мы передадим его с рождественскими эльфами 🧝🏻",
                "Не забудьте поздравить и тех, кто не из клуба! ☃️",
                "Оно попало прямо под ёлочку 🎁",
                "Сезон праздников начинается, самое время вайбить! 🎇",
                "Что ж, а теперь пора праздновать! 🍾",
            ]
        ),
    )


def unexpected_day(
    sender: User, recipient: User | None = None
) -> tuple[bool, _Message]:
    notifications = [
        "{sender} заметил то, что старалось быть незамеченным.",
        "{sender} стал свидетелем процесса, который не был запланирован.",
        "Аномалия, обнаруженная {sender}, передана в профильный отдел анализа аномалий.",
        "Благодаря {sender} стало ясно, что всё не так просто.",
        "В ходе наблюдения {sender} были зафиксированы отклонения от штатного режима.",
        "Обнаруженное {sender} отправлено на дальшейшее изучение.",
        "По версии {sender}, происходит нечто подозрительно неклассифицируемое.",
        "По информации {sender}, происходит некое несоответствие установленным параметрам.",
        "Сигнал, поступивший от {sender}, классифицирован как нестандартный.",
        "Согласно наблюдениям {sender}, стабильность нестабильна.",
    ]

    return True, _Message(
        title="Об этом инциденте теперь знают все 👾",
        message=random.choice(
            [
                "Дальше ситуация находится под контролем 🇦🇶️",
                "Запущен внутренний протокол реагирования 📡",
                "Истинная причина будет выяснена 👽",
                "Материалы переданы в профильные агентства 🛸",
                "Начата проверка по всем каналам 🔮",
                "Ответственные подразделения уже уведомлены 🕵️🏻",
            ]
        ),
    )


ANTIC_HANDLERS = {
    "new_year": new_year,
    "new_year_private": new_year_private,
    "valentine_common": valentine_common,
    "valentine": valentine,
    "valentine_anonymous": valentine_anonymous,
    "leap_day": leap_day,
    "fools_day": fools_day,
    "cosmonautics_day": cosmonautics_day,
    "club_birthday": club_birthday,
    "summer_solstice": summer_solstice,
    "friends_day": friends_day,
    "friends_day_private": friends_day_private,
    "cats_day": cats_day,
    "cats_day_private": cats_day_private,
    "testers_day": testers_day,
    "halloween": halloween,
    "coffees_day": coffees_day,
    "western_christmas": western_christmas,
    "western_christmas_private": western_christmas_private,
    "unexpected_day": unexpected_day,
    "miss": miss,
}
