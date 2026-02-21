import logging
import random
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from django.core.cache import cache
from django_q.tasks import async_task
from typing import TypedDict, ClassVar, Literal
from telegram import ParseMode

from fun.utils import get_new_banek
from notifications.telegram.common import send_telegram_message, Chat, CLUB_CHAT
from users.models.user import User


log = logging.getLogger(__name__)

MIN = 60
HOUR = 60 * MIN
DAY = 24 * HOUR
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


class AnticBase:
    name: ClassVar[str]
    type: ANTIC_TYPE
    date: tuple[int, int]
    duration: int  # days
    link: _Link

    global_cooldown: ClassVar[int] = 0  # for common chat notifications
    user_cooldown: ClassVar[int] = 30  # general user cd and for check single click

    notifications: list[str] = []
    success_messages: _MessageTemplate = {
        "title": "Ура, доставлено 🌟",
        "message_texts": [
            "Всё успешно отправлено, сценарий Seele выполнен в точности 📱",
        ],
    }
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
    # === inner things

    not_today_errors: _MessageTemplate = {
        "title": "Ой, это не должно произойти сегодня 📆",
        "message_texts": [
            "Подожди чуть-чуть и попробуй ещё раз в нужное время 👁️👁️",
            "А сегодня можешь почитать пост:\n\n https://vas3k.club/post/random/",
            "Кажется, все даты решили перепутаться 🤖",
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
        "title": "Ой! Кажется, вы это недавно нажимали 🧐",
        "message_texts": [
            "Мы бы и рады помочь, но это же кнопочка, мы её не можем контролировать 😳",
            "Блин, и что делать? О, можно почитать пост:\n\n https://vas3k.club/post/random/",
            "Похоже, теперь эта кнопочка сломалась. Придётся её чинить 🗜️",
        ],
    }
    no_telegram_errors: _MessageTemplate = {
        "title": "Мы не смогли доставить посылку 😮",
        "message_texts": [
            "Получатель не привязал телеграм. Мы так не играем! 🤥",
            "Получатель предпочёл скрыть от нас телеграм. Вот и пусть сидит без уведомляшек! 👅",
            "Возможно, получатель скрылся от мира. По крайней мере, мы не нашли его телеграм 🥷",
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
    def make_message(template: _MessageTemplate) -> _Message:
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
        if cls.global_cooldown:
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
        if cls.global_cooldown:
            cache.set(f"fun:antic:{cls.name}", True, timeout=cls.global_cooldown)

    @classmethod
    def _set_user_cooldown(cls, sender: User) -> None:
        cache.set(f"fun:antic:{cls.name}:{sender.id}", True, timeout=cls.user_cooldown)

    @classmethod
    def _set_already_send(cls, sender: User, recipient: User | None) -> None:
        if recipient:
            cache.set(
                f"fun:antic:{cls.name}:{sender.id}:{recipient.id}",
                True,
                timeout=cls.duration * DAY,
            )

    # === main methods

    @classmethod
    def is_displayable(cls, type: str, sender: User, recipient: User | None) -> bool:
        if (
            cls.type != type
            or not cls._is_today()
            or cls._is_global_cooldown_active()
            or cls._is_user_cooldown_active(sender)
        ):
            return False

        # in practice due to template filter limitations these checks are not used
        if recipient and (
            sender.id == recipient.id
            or not recipient.telegram_id
            or cls._is_already_sent(sender, recipient)
        ):
            return False

        return True

    @classmethod
    def handle(
        cls, sender: User, recipient: User | None = None
    ) -> tuple[bool, _Message]:
        if not cls._is_today():
            return False, cls.make_message(cls.not_today_errors)
        if cls._is_global_cooldown_active():
            return False, cls.make_message(cls.global_cooldown_errors)
        if cls._is_user_cooldown_active(sender):
            return False, cls.make_message(cls.user_cooldown_errors)

        if cls.type == "private" and not recipient:
            return False, cls.make_message(cls.no_telegram_errors)
        if recipient:
            if sender.id == recipient.id:
                return False, cls.make_message(cls.its_you_errors)
            if not recipient.telegram_id:
                return False, cls.make_message(cls.no_telegram_errors)
            if cls._is_already_sent(sender, recipient):
                return False, cls.make_message(cls.already_send_errors)

        try:
            cls.handler(sender, recipient)
        except Exception as exc:
            log.warning(f"Error handling antic: {exc}")
            return False, cls.make_message(cls.default_errors)

        cls._set_global_cooldown()
        cls._set_user_cooldown(sender)
        cls._set_already_send(sender, recipient)

        return True, cls.make_message(cls.success_messages)

    @classmethod
    def handler(cls, sender: User, recipient: User | None) -> None:
        text = random.choice(cls.notifications).format(
            sender=f"[{sender.full_name}]({sender.club_profile_link})"
        )
        async_task(
            send_telegram_message,
            chat=Chat(id=recipient.telegram_id) if recipient else CLUB_CHAT,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )


# === antics ===


class NewYear(AnticBase):
    name = "new_year"
    type = "common"
    date = (12, 31)
    duration = 2
    global_cooldown = 30 * MIN
    user_cooldown = duration * DAY

    link = {"icon": "gifts", "label": "Навайбить!"}
    success_messages = {
        "title": "Поздравление улетело поздравлять ❄️",
        "message": [
            "А все причастные поздравляют тебя в ответ! 🎄",
            "И тебя тоже с праздником! 🎆",
            "Клубни получили новогоднее поздравление 🎁",
            "Новый год начал обрабатываться 🌟",
            "Теперь самое время отвлечься от экранов и пойти праздновать 🥂",
            "Хо-хо-хо, Новый год стал новогоднее 🎅",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class NewYearPrivate(AnticBase):
    name = "new_year_private"
    type = "private"
    date = (12, 31)
    duration = 2
    user_cooldown = 3 * HOUR

    link = {"icon": "🎅🏻", "label": "Поздравить с Новым Годом"}
    success_messages = {
        "title": "Поздравление улетело клубню 📨",
        "message": [
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
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class ValentineCommon(AnticBase):
    name = "valentine_common"
    type = "common"
    date = (2, 14)
    duration = 1
    global_cooldown = 1 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "heart", "label": "Выдать любовь!"}
    success_messages = {
        "title": "Вы публично рассказали свою любовь ☺️",
        "message": [
            "Клубни растроганы и слегка смущены 🌹",
            "Любовь синхронизирована 💞",
            "Причастные радостно получили сердечки 💖",
            "Сегодня разрешено быть сентиментальным 💝",
            "Эмоции доставлены в целости и нежности ❤",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class Valentine(AnticBase):
    name = "valentine"
    type = "private"
    date = (2, 14)
    duration = 1
    user_cooldown = 1 * HOUR

    link = {"icon": "💝", "label": "Отправить валентинку"}
    success_messages = {
        "title": "Шоколадка передана 🍫",
        "message": [
            "Теперь адресат знает, что вы его цените 💑🏻",
            "Правильно, любовь нужно дарить 💞",
            "Много любви не бывает 💕",
            "Не забудь, что тебя тоже любят! 🩷",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class ValentineAnonymous(AnticBase):
    name = "valentine_anonymous"
    type = "private"
    date = (2, 14)
    duration = 1
    user_cooldown = 3 * HOUR

    link = {"icon": "💖", "label": "Отправить анонимку"}
    success_messages = {
        "title": "Валентинка отправлена 💌",
        "message": [
            "В мире стало чуть больше любви. И чуть больше неизвестности 🥷",
            "И мы передали её абсолютно анонимно 🤿",
            "И пусть адресат теперь гадает, от кого она 💟",
            "Но получатель не узнает, кто её отправил 🕵️🏻‍️",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class LeapDay(AnticBase):
    name = "leap_day"
    type = "common"
    date = (2, 29)
    duration = 1
    global_cooldown = 2 * DAY

    link = {"icon": "calendar-alt", "label": "Зафиксировать!"}
    success_messages = {
        "title": "Вы зафиксировали временной парадокс 👀",
        "message": [
            "Пусть все его наблюдают! 👓",
            "Следующий раз такое будет нескоро 🕖",
            "Этим вы сломали все наши даты 🔐",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class FoolsDay(AnticBase):
    name = "fools_day"
    type = "common"
    date = (4, 1)
    duration = 1
    global_cooldown = 2 * HOUR

    link = {"icon": "laugh", "label": "Наклоунадничать!"}
    success_messages = {
        "title": "Анекдот улетел куда надо 🤡",
        "message": [
            "Беги тоже его скорее читай 🎠",
            "Можно расслабиться и просто подурачиться 🪅",
            "И на что мы только тратим электроэнергию...",
            "А где надо армяне в нарды играют ♟️",
            "А куда надо ему как раз! 🎩",
            "Прилетел туда и сгорел 🐻",
            "Но есть один нюанс ☝",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        text = "_Анекдот по заказу от {sender}:_\n\n{banek}".format(
            sender=f"[{sender.full_name}]({sender.club_profile_link})",
            banek=get_new_banek(),
        )
        async_task(
            send_telegram_message,
            chat=CLUB_CHAT,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )


class CosmonauticsDay(AnticBase):
    name = "cosmonautics_day"
    type = "common"
    date = (4, 12)
    duration = 1
    global_cooldown = 4 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "rocket", "label": "Стартовать!"}
    success_messages = {
        "title": "Поздравление улетело 🚀",
        "message": [
            "Бип-бип-бип-бип, поздравление отправлено в чат 🛰️",
            "Сигнал совершил круг вокруг всей Земли, чтобы прилететь в чат 🌍",
            "Следующая остановка - Марс 👨‍🚀",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class ClubBirthday(AnticBase):
    name = "club_birthday"
    type = "common"
    date = (4, 15)
    duration = 1
    global_cooldown = 2 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "birthday-cake", "label": "Поздравить!"}
    success_messages = {
        "title": "Ура, Клуб поздравлен 🎉",
        "message": [
            "Все червячки отправились на праздник 🪱",
            "Держи тортик 🍰",
            "Еее, празднуем! 🎆",
            "Задуваем свечи и загадываем долгую счастливую жизнь (для Клуба) 🎂",
            "Тусим-тусим, праздник! 🎊",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class SummerSolstice(AnticBase):
    name = "summer_solstice"
    type = "common"
    date = (6, 21)
    duration = 1
    global_cooldown = 1 * DAY

    link = {"icon": "sun", "label": "Подсветить!"}
    success_messages = {
        "title": "На сегодняшнюю дату пролит свет ☀",
        "message": [
            "Несите дрова и медвежью шкуру! 🔥",
            "И да, уже почти прошёл июнь 🌞",
            "Кстати, держи венок, сегодня ты - Королева мая 🌼🌼🌼🌼",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class FriendsDay(AnticBase):
    name = "friends_day"
    type = "common"
    date = (7, 30)
    duration = 1
    global_cooldown = 2 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "smile", "label": "Подружиться!"}
    success_messages = {
        "title": "Клубни поздравлены и дружелюбны 🧑‍🤝‍🧑",
        "message": [
            "А ещё дружба - не только станция метро в Ереване, держим в курсе 🍕",
            "Дружба, мир, жвачка! 🧙🏻‍♂️",
            "Мы все теперь друзяшки! 🤠",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class FriendsDayPrivate(AnticBase):
    name = "friends_day_private"
    type = "private"
    date = (7, 30)
    duration = 1
    user_cooldown = 31 * HOUR

    link = {"icon": "👯‍♂️", "label": "Признаться в дружбе"}
    success_messages = {
        "title": "Друг поздравлен 💅",
        "message": [
            "Дружба - это весело! Давайте дружить все?",
            "Кстати, глянь, где лежат [все друзяшки](/user/me/friends/).",
            "Теперь он знает, что он ваш друг. Наверное.",
            "Ты можешь поздравить и остальных своих друзей.\nПогоди, ты что, плачешь?",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class CatsDay(AnticBase):
    name = "cats_day"
    type = "common"
    date = (8, 8)
    duration = 1
    global_cooldown = 4 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "cat", "label": "Помурлыкать!"}
    success_messages = {
        "title": "Чат успешно назван котятами 🐱",
        "message": [
            "Все массово мурлыкают 😻",
            "И ты тоже котик 🐈",
            "Мяв. Мяв. Мур 🐈",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class CatsDayPrivate(AnticBase):
    name = "cats_day_private"
    type = "private"
    date = (8, 8)
    duration = 1
    user_cooldown = 4 * HOUR

    link = {"icon": "😺", "label": "Обозвать котиком"}
    success_messages = {
        "title": "Адресат получил мявобщение 😼",
        "message": [
            "А глянь, какой ещё в Клубе есть [котик](https://vas3k.club/user/me/)!",
            "Мявмяв мяяв мур мявмяв. Мяв.\n\nВпрочем, забейте, это был _КОТОМБУР_.",
            "Надеемся, у него нет собаки. А то придётся лезть на дерево 🙀",
            "Ну вот, скатываемся. Точнее, _СКОТЫВАЕМСЯ_ 🐈",
            "Теперь вам придётся его гладить и кормить несколько раз в день 🐟",
            "Теперь он котик. И ты котик.",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class TestersDay(AnticBase):
    name = "testers_day"
    type = "common"
    date = (9, 9)
    duration = 1
    global_cooldown = 4 * HOUR

    link = {"icon": "bug", "label": "Создать баги!"}
    success_messages = {
        "title": "Баги ÑƒÑ�Ð¿ÐµÑˆÐ½Ð¾ созданы 🪲",
        "message": [
            "[На главную](/user/me/edit/account/)",
            "{% MESSAGE_DETAILS_TEXT %}",
            "А сюда [.button.button-red НЕ НАЖИМАТЬ](/label/wow/)",
            "Было оповещено {receiver_count} человек.",
            "ЭТО СООБЩЕНИЕ ПОПАЛО СЮДА ПО НЕДОСМОТРУ РЕВЬЮЕРОВ ХЕХЕХЕ 🚨",
            '<a href="https://vas3k.club/">Вернуться на главную</a>',  # plain text
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class Halloween(AnticBase):
    name = "halloween"
    type = "common"
    date = (10, 31)
    duration = 1
    global_cooldown = 1 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "skull", "label": "Напугать!"}
    success_messages = {
        "title": "Хехехе, чат напуган 🎃",
        "message": [
            "**БУУУУ** 👻\n\nИ вы теперь напуганы.",
            "А вы задумывались, почему тыквенный спас ассоциируют со всякими пугалками? 🤔",
            "Но не переживайте, они всё понимают 🍁",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class CoffeesDay(AnticBase):
    name = "coffees_day"
    type = "common"
    date = (10, 1)
    duration = 1
    global_cooldown = 4 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "mug-hot", "label": "Накофеинить!"}
    success_messages = {
        "title": "Кофе в процессе доставки 🐌",
        "message": [
            "Чат можно было и пожалеть, там и так уже все от кофетрясутся! ☕",
            "Самое время лечь поспать 😴",
            "Теперь они немного более кофеинезированы ☕",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class WesternChristmas(AnticBase):
    name = "western_christmas"
    type = "common"
    date = (12, 25)
    duration = 2
    global_cooldown = 2 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "gift", "label": "Дать подарок!"}
    success_messages = {
        "title": "Чат поздравлен 💫",
        "message": [
            "Заваривайте чашечку глинтвейна и залетайте с ним в"
            " [Бар](https://vas3k.club/room/bar/chat/) 🥃",
            "И тебя с праздником! 🎄",
            "Он родился. А что произошло дальше, мы с вами сейчас и узнаем 🐙",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class WesternChristmasPrivate(AnticBase):
    name = "western_christmas_private"
    type = "private"
    date = (12, 25)
    duration = 2
    user_cooldown = 3 * HOUR

    link = {"icon": "🎁", "label": "Поздравить с рождеством"}
    success_messages = {
        "title": "Поздравление улетело 💫",
        "message": [
            "А что это ещё летит? А, это вайб на подлёте! Вот он: ✨✨✨",
            "Мы передадим его с рождественскими эльфами 🧝🏻",
            "Не забудьте поздравить и тех, кто не из клуба! ☃️",
            "Оно попало прямо под ёлочку 🎁",
            "Сезон праздников начинается, самое время вайбить! 🎇",
            "Что ж, а теперь пора праздновать! 🍾",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
        pass


class UnexpectedDay(AnticBase):
    name = "unexpected_day"
    type = "bottom_link"
    date = (random.randint(1, 12), random.randint(1, 28))
    duration = random.randint(1, 3)
    global_cooldown = duration * DAY

    link = {"icon": "", "label": "Ничего подозрительного тут"}
    success_messages = {
        "title": "Об этом инциденте теперь знают все 👾",
        "message": [
            "Дальше ситуация находится под контролем 🇦🇶️",
            "Запущен внутренний протокол реагирования 📡",
            "Истинная причина будет выяснена 👽",
            "Материалы переданы в профильные агентства 🛸",
            "Начата проверка по всем каналам 🔮",
            "Ответственные подразделения уже уведомлены 🕵️🏻",
        ],
    }

    @classmethod
    def handler(cls, sender: User, recipient: User | None = None) -> None:
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


ANTICS = [
    NewYear,
    NewYearPrivate,
    ValentineCommon,
    Valentine,
    ValentineAnonymous,
    LeapDay,
    FoolsDay,
    CosmonauticsDay,
    ClubBirthday,
    SummerSolstice,
    FriendsDay,
    FriendsDayPrivate,
    CatsDay,
    CatsDayPrivate,
    TestersDay,
    Halloween,
    CoffeesDay,
    WesternChristmas,
    WesternChristmasPrivate,
    UnexpectedDay,
]
ANTICS_MAP = {antic.name: antic for antic in ANTICS}
