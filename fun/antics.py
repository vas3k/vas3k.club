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
    errors: _MessageTemplate = {
        "title": "Что-то произошло, но мы не знаем, что 🐞",
        "message_texts": [
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

    @classmethod
    def can_send_notification(
        cls, sender: User, recipient: User | None = None
    ) -> bool:
        if (
            not cls._is_today()
            or cls._is_global_cooldown_active()
            or cls._is_user_cooldown_active(sender)
            or not sender.is_active_member
        ):
            return False

        if cls.type == "private" and not recipient:
            return False

        if recipient and (
            sender.id == recipient.id
            or not recipient.telegram_id
            or not recipient.is_active_member
            or cls._is_already_sent(sender, recipient)
        ):
            return False

        return True

    @classmethod
    def handle(cls, sender: User, recipient: User | None = None) -> _Message:
        if not cls.can_send_notification(sender, recipient):
            return cls.make_message(cls.errors)

        try:
            cls.handler(sender, recipient)
        except Exception as exc:
            log.warning(f"Error handling antic: {exc}")
            return cls.make_message(cls.errors)

        cls._set_global_cooldown()
        cls._set_user_cooldown(sender)
        cls._set_already_send(sender, recipient)

        return cls.make_message(cls.success_messages)

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
    notifications = [
        "{sender} поздравляет с Новым годом! 🎄",
        "{sender} желает всем самого доброго в новом году! 🎅🏻",
        "{sender} желает самых красивых салютов за окном! 🎆",
        "{sender} отправляет снежинки вайба всем! ❄️",
        "{sender} чокается со всеми шампанским! 🥂",
        "{sender} передаёт всем самых крутых новогодних поздравлений! ☃️",
        "{sender} делится новогодним настроением! ✨",
        "{sender} отправляет всем мешок новогодней магии! 🌟",
        "{sender} поднимает бокал за каждого здесь! 🥂",
        "{sender} добавляет немного волшебства в этот год! 🪄",
        "{sender} желает всем уютных вечеров и смелых планов! 🎁",
        "{sender} желает всем стать лучшей версией себя в новом году! 🍾",
        "{sender} желает всем меньше багов и больше чудес! 💫",
        "{sender} зажигает пачку бенгалек! 💥",
        "{sender} варит всем в чате вкусный глинтвейн! 🍷",
        "{sender} раздаёт всем в чате воображаемые подарки! 🎁",
    ]
    success_messages = {
        "title": "Поздравление улетело поздравлять ❄️",
        "message_texts": [
            "А все причастные поздравляют тебя в ответ! 🎄",
            "И тебя тоже с праздником! 🎆",
            "Клубни получили новогоднее поздравление 🎁",
            "Теперь самое время отвлечься от экранов и пойти праздновать 🥂",
            "Хо-хо-хо, Новый год стал новогоднее 🎅",
        ],
    }


class NewYearPrivate(AnticBase):
    name = "new_year_private"
    type = "private"
    date = (12, 31)
    duration = 2
    user_cooldown = 30 * MIN

    link = {"icon": "🎅🏻", "label": "Поздравить с Новым Годом"}
    notifications = [
        "{sender} поздравляет тебя с Новым годом! 🎄",
        "{sender} передаёт поздравления с Новым годом! 🎆",
        "{sender} желает самого вайбового Нового года! ☃️",
        "{sender} делится вайбом прямо из-под ёлки. С Новым годом! 🎄",
        "От {sender} тебе послание:\n_С Новым годом!_ 🎅🏻",
        "{sender} желает круто отпраздновать Новый год! 🌟",
        "{sender} отправляет лучшие пожелания в новом году! ✨",
        "{sender} чокается с тобой шампанским! С Новым годом! 🥂",
        "{sender} поздравляет с Новым годом и запускает фейерверк! 🎇",
        "{sender} передаёт подарков и желает офигенного Нового года! 🎁",
    ]
    success_messages = {
        "title": "Поздравление улетело клубню 📨",
        "message_texts": [
            "Адресат уже мысленно чокается с тобой 🥂",
            "Он стал чуточку счастливее 🎁",
            "Он там по ту сторону экрана улыбается, кстати (возможно, виноват глинтвейн).",
            "Праздник аккуратно передан точно в руки 🎄",
            "Теперь у адресата официально праздничное настроение 📜",
        ],
    }


class ValentineCommon(AnticBase):
    name = "valentine_common"
    type = "common"
    date = (2, 14)
    duration = 1
    global_cooldown = 1 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "heart", "label": "Выдать любовь!"}
    notifications = [
        "{sender} передаёт:\n_Я всех вас очень люблю!_ 💖",
        "{sender} раздаёт всем в этом чатике валентинок! 💌",
        "{sender} хочет сообщить о своей любви ко всем вам! 💞",
        "{sender} признаётся во всеобщей любви! 💓",
        "Немного любви в чатик: {sender} всех очень любит! 💗",
        "{sender} передаёт всем вам валентинки с признанием! 💌",
        "Внимание! {sender} всех вас очень любит! 🩷",
        "{sender} всем очень хочет рассказать о своей любви 💝!",
        "{sender} шлёт в чат немного любви и хорошего настроения! 🥰",
        "{sender} поздравляет всех с 14 февраля! 💖",
        "{sender} желает всем любви и внимания! 💗",
        "{sender} желает всем любви и тела! 💓",
    ]
    success_messages = {
        "title": "Вы публично рассказали свою любовь ☺️",
        "message_texts": [
            "Клубни растроганы и слегка смущены 🌹",
            "Причастные радостно получили сердечки 💖",
            "Эмоции доставлены в целости и нежности ❤",
        ],
    }


class Valentine(AnticBase):
    name = "valentine"
    type = "private"
    date = (2, 14)
    duration = 1
    user_cooldown = 30 * MIN

    link = {"icon": "💝", "label": "Отправить валентинку"}
    notifications = [
        "{sender} отправил тебе валентинку! 💌",
        "{sender} решил признаться в своих чувствах! 💖",
        "У тебя новая валентинка от {sender}! 💓",
        "Принимай валентинку! Она от {sender} ❤️",
        "{sender} подкинул тебе что-то. Ой, это же валентинка! 💘",
        "Пришла новая валентинка. Отправитель - {sender} 😍",
        "Тебе что-то пришло. А, это валентинка от {sender}! 💌",
        "Передаём тебе валентинку от {sender}. Он тебя любит! 💖",
        "{sender} немного смущённо передаёт тебе валентинку 🩷",
        "Держи. Это валентинка от {sender} 💝",
    ]
    success_messages = {
        "title": "Шоколадка передана 🍫",
        "message_texts": [
            "Теперь адресат знает, что вы его цените 💑🏻",
            "Правильно, любовь нужно множить 💞",
            "Много любви не бывает 💕",
            "Не забудь, что тебя тоже любят! 🩷",
        ],
    }


class ValentineAnonymous(AnticBase):
    name = "valentine_anonymous"
    type = "private"
    date = (2, 14)
    duration = 1
    user_cooldown = 2 * HOUR

    link = {"icon": "💖", "label": "Отправить анонимку"}
    notifications = [
        "Кто-то неизвестный отправил тебе валентинку! 💕",
        "Вау! У тебя новая валентинка! 💌 Она от ⬛⬛⬛⬛⬛",
        "Тебе передали валентинку!\nОтправитель неизвестен 💝",
        "У тебя новая валентинка от тайного поклонника! 💌",
        "Новая валентинка уже ждёт тебя. От кого? Секрет 💗",
        "Кто-то решил отправить тебе валентинку. Подписаться забыл 💖",
        "Кто-то анонимный решил порадовать тебя валентинкой 💌",
        "Тебе пришла валентинка от кого-то неизвестного ✨",
        "Невыясненная личность подкинула тебе валентинку и призналась в любви 💝",
        "Получена новая валентинка. Отправитель не подписался 💝",
    ]
    success_messages = {
        "title": "Валентинка отправлена 💌",
        "message_texts": [
            "В мире стало чуть больше любви. И чуть больше неизвестности 🥷",
            "И мы передали её абсолютно анонимно 🤿",
            "И пусть адресат теперь гадает, от кого она 💟",
            "Но получатель не узнает, кто её отправил 🕵️🏻‍️",
        ],
    }


class LeapDay(AnticBase):
    name = "leap_day"
    type = "common"
    date = (2, 29)
    duration = 1
    global_cooldown = duration * DAY

    link = {"icon": "calendar-alt", "label": "Зафиксировать!"}
    notifications = [
        "{sender} решил напомнить, что сегодня странное число 📆",
        "Вы знаете, какое сегодня число? {sender} напоминает: странное 🗓️",
        "Раз в четыре года происходят временные парадоксы. {sender} обращает внимание,"
        " что сейчас он 📅",
        "Странный год. Как заметил {sender}, его пережить чуть сложнее - он идёт дольше ⏳",
    ]
    success_messages = {
        "title": "Вы зафиксировали временной парадокс 👀",
        "message_texts": [
            "Пусть все его наблюдают! 👓",
            "Следующий раз такое будет нескоро 🕖",
        ],
    }


class FoolsDay(AnticBase):
    name = "fools_day"
    type = "common"
    date = (4, 1)
    duration = 1
    global_cooldown = 2 * HOUR

    link = {"icon": "laugh", "label": "Наклоунадничать!"}
    success_messages = {
        "title": "Анекдот улетел куда надо 🤡",
        "message_texts": [
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
        text = "_Анекдот по заказу от_ {sender}:\n\n{banek}".format(
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
    global_cooldown = duration * DAY

    link = {"icon": "rocket", "label": "Стартовать!"}
    notifications = [
        "{sender} поздравляет всех с Днём космонавтики! 🌌",
        "{sender} отправляет поздравления с Днём космонавтики 🚀",
        "{sender} заметил, что сегодня праздник. С Днём космонавтики! 🌠",
        "С орбиты идёт новый сигнал.\nЭто {sender} поздравляет всех с Днём"
        " космонавтики! 🛰️",
    ]
    success_messages = {
        "title": "Поздравление улетело 🚀",
        "message_texts": [
            "Бип-бип-бип-бип, поздравление отправлено в чат 🛰️",
            "Сигнал совершил круг вокруг всей Земли, чтобы прилететь в чат 🌍",
            "Следующая остановка - Марс 👨‍🚀",
        ],
    }


class ClubBirthday(AnticBase):
    name = "club_birthday"
    type = "common"
    date = (4, 13)
    duration = 1
    global_cooldown = 2 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "birthday-cake", "label": "Поздравить!"}
    notifications = [
        "Сегодня День рождения Клуба! {sender} передаёт всем поздравления! 🎊",
        "{sender} поздравляет всех с Днём рождения Клуба! 🎉",
        "Всех с Днём рождения Клуба! И всем поздравления от {sender} 🎈",
        "Поздравления от {sender}: всех с Днём рождения Клуба! 🎂",
        "{sender} напоминает, что сегодня День рождения клуба, и поздравляет с этим! 🥳",
        "С Днём рождения Клуба! {sender} передаёт всем поздравления! 🎊",
        "Как известно, у Клуба День рождения. {sender} всех поздравляет! 🥳",
        "Сегодня Клубу ещё +1 год. {sender} всех поздравляет! 🎉",
        "{sender} поздравляет с ещё одним годом жизни Клуба! 🎇",
        "Клуб празднует День рождения, а {sender} всех поздравляет!🎈",
        "С Днём рождения Клуба! {sender} добавляет свои поздравления! 🎉",
        "{sender} передаёт поздравления в честь Дня рождения Клуба! 🥳",
    ]
    success_messages = {
        "title": "Ура, Клуб поздравлен 🎉",
        "message_texts": [
            "Все червячки отправились на праздник 🪱",
            "Держи тортик 🍰",
            "Еее, празднуем! 🎆",
            "Задуваем свечи и загадываем долгую счастливую жизнь (для Клуба) 🎂",
            "Тусим-тусим, праздник! 🎊",
        ],
    }


class SummerSolstice(AnticBase):
    name = "summer_solstice"
    type = "common"
    date = (6, 21)
    duration = 1
    global_cooldown = duration * DAY

    link = {"icon": "sun", "label": "Подсветить!"}
    notifications = [
        "{sender} раздаёт всем цветочные короны: сегодня солнцестояние\n🌼🌼🌼🌼",
        "{sender} напоминает, что сегодня день солнцестояния. И просит отойти"
        " подальше от скал 🧗🏻",
        "{sender} _подсвечивает_ тот факт, что сегодня солнышко поднимается выше всего 🌞",
        "{sender} предлагает идти танцевать вокруг Майского дерева: сегодня солнцестояние 🌿",
    ]
    success_messages = {
        "title": "На сегодняшнюю дату пролит свет ☀",
        "message_texts": [
            "Несите дрова и медвежью шкуру! 🔥",
            "И да, уже почти прошёл июнь 🌞",
        ],
    }


class FriendsDay(AnticBase):
    name = "friends_day"
    type = "common"
    date = (7, 30)
    duration = 1
    global_cooldown = 2 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "smile", "label": "Подружиться!"}
    notifications = [
        "{sender} желает каждому надёжных людей рядом! 🫂",
        "С днём дружбы! {sender} передаёт, что вы все - крутые друзяки! 🤗",
        "{sender} считает, что этот чат очень дружный! Всех с Днём друзяшек! 👯",
        "{sender} поздравляет с Днём дружбы и желает взаимной поддержки! 😊",
        "{sender} передаёт: вы все очень крутые и дружелюбные! 🫶🏻",
        "{sender} поздравляет всех с Днём дружбы и желает крепких связей! 🤝",
        "{sender} отправляет в чат немного дружеского вайба! ✨",
        "{sender} шлёт всем дружеского тепла в честь Дня дружбы! 💛",
        "{sender} поздравляет с Днём дружбы и желает самых крутых друзей! 💛",
        "{sender} желает всем поводов чаще собираться вместе! 🫂",
    ]
    success_messages = {
        "title": "Клубни поздравлены и дружелюбны 🧑‍🤝‍🧑",
        "message_texts": [
            "А ещё дружба - не только станция метро в Ереване, держим в курсе 🍕",
            "Дружба, мир, жвачка! 🧙🏻‍♂️",
            "Мы все теперь друзяшки! 🤠",
        ],
    }


class FriendsDayPrivate(AnticBase):
    name = "friends_day_private"
    type = "private"
    date = (7, 30)
    duration = 1
    user_cooldown = 1 * HOUR

    link = {"icon": "👯‍♂️", "label": "Признаться в дружбе"}
    notifications = [
        "{sender} решил признаться вам. Вы - друзяки! 🤗",
        "{sender} передал, что очень с вами дружит! 🤠",
        "{sender} напоминает: вы - друзья! ✨",
        "{sender} хочет вам признаться в том, что вы друзья 🧙🏻",
        "Вы, конечно, знаете, но вы с {sender} друзья 🥺",
        "Напоминание от {sender}: вы с ним друзья! 🌞",
        "От {sender} пришла информация: вы с ним друзья! 🥳",
        "Чтобы вы не забывали, {sender} напоминает: вы друзья 🍕",
        "Вы с {sender} - друзья. Напоминаем и поздравляем 🌟",
    ]
    success_messages = {
        "title": "Друг поздравлен 💅",
        "message_texts": [
            "Дружба - это весело! Давайте дружить все?",
            "Кстати, глянь, где лежат [все друзяшки](/user/me/friends/).",
            "Теперь он знает, что он ваш друг. Наверное.",
            "Ты можешь поздравить и остальных своих друзей.\nПогоди, ты что, плачешь?",
        ],
    }


class CatsDay(AnticBase):
    name = "cats_day"
    type = "common"
    date = (8, 8)
    duration = 1
    global_cooldown = 4 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "cat", "label": "Помурлыкать!"}
    notifications = [
        "{sender} напоминает, что вы все котики! 🐱",
        "{sender} обзывается! Если точнее, говорит, что вы все котики! 🐈",
        "{sender} поздравляет с Днём котиков. То есть с вашим днём! 🐱",
        "С Днём котиков! {sender} напоминает, что это вы! 🐈",
        "Напоминание от {sender}: вы все котики! 😺",
        "_Загадка от_ {sender}:\n\nЧто делают коровки? Мычат.\nЧто делают собачки?"
        " Гавкают.\nЧто делают котики?\n\n_Ответ: сидят в этом чатике_ 😼",
        "{sender} желает вас всем быть поглаженными. Потому что вы все котики! 🐱",
        "Если кто-то забыл, то сегодня День котиков.\nИ {sender} объявляет"
        " массовое мурлыкание! 😻",
    ]
    success_messages = {
        "title": "Чат успешно назван котятами 🐱",
        "message_texts": [
            "Все массово мурлыкают 😻",
            "И ты тоже котик 🐈",
            "Мяв. Мяв. Мур 🐈",
        ],
    }


class CatsDayPrivate(AnticBase):
    name = "cats_day_private"
    type = "private"
    date = (8, 8)
    duration = 1
    user_cooldown = 3 * HOUR

    link = {"icon": "😺", "label": "Обозвать котиком"}
    notifications = [
        "{sender} назвал тебя котиком 🐈",
        "{sender} считает, что ты котик 🐈",
        "{sender} говорит:\n_- Мур мявмяв мяв мурмур._\n\nРаз котик ты, то ты и читай 😼",
        "{sender} передаёт, что ты котик 😻",
        "{sender} показывает тебе твой портрет. Вот он:\n\n🐱",
        "{sender} передал тебе расчёску 🪮\nЭто потому что ты котик.",
        "{sender} уверен, что ты котик 😽",
    ]
    success_messages = {
        "title": "Адресат получил мявобщение 😼",
        "message_texts": [
            "А глянь, какой ещё в Клубе есть [котик](https://vas3k.club/user/me/)!",
            "Мявмяв мяяв мур мявмяв. Мяв.\n\nВпрочем, забейте, это был _КОТОМБУР_.",
            "Надеемся, у него нет собаки. А то придётся лезть на дерево 🙀",
            "Ну вот, скатываемся. Точнее, _СКОТЫВАЕМСЯ_ 🐈",
            "Теперь вам придётся его гладить и кормить несколько раз в день 🐟",
            "Теперь он котик. И ты котик.",
        ],
    }


class TestersDay(AnticBase):
    name = "testers_day"
    type = "common"
    date = (9, 9)
    duration = 1
    global_cooldown = 4 * HOUR

    link = {"icon": "bug", "label": "Создать баги!"}
    notifications = [
        "{sender} хотел создать пару багов.\nНо у него не получилось:"
        " для этого нужен тариф {{ tariff.name }} и выше.",
        "🪲🪲🪲🪲🪲🪲\nО нет, сюда проникли баги! Это всё {sender}!",
        "{sender} подкинул немного багов для {{ recipient.full_name }}!",
        "Хм, что-то пошло не так. Как будто, {sender} СЃРѕР·РґР°Р» Р±Р°РіРё СЃ"
        " РєРѕРґРёСЂРѕРІРєРѕР№.",
        "_У нас важное сообщение от_ {sender}:\n\n_null_ tester's day _null_",
        "*Fatal error*: {sender} {{ action }} to {{ chat.name }}",
        "\"<bound method User.congratulate arg=(id=42, name='{sender}', reason='TESTER_DAY')>\"",
        "*Новое сообщение:*\n\nНа связи {sender}, всех с днём тестировщика! Гляньте,"
        " чо есть; DROP TABLE users;\n\n_автор: <user not found>_",
        "<User(id=1337, name={sender}> поздравляет всех с днём тестировщика!",
    ]
    success_messages = {
        "title": "Баги ÑƒÑ�Ð¿ÐµÑˆÐ½Ð¾ созданы 🪲",
        "message_texts": [
            "[На главную](/user/me/edit/account/)",
            "{% MESSAGE_DETAILS_TEXT %}",
            "А сюда [.button.button-red НЕ НАЖИМАТЬ](/label/wow/)",
            "Было оповещено {receiver_count} человек.",
            "ЭТО СООБЩЕНИЕ ПОПАЛО СЮДА ПО НЕДОСМОТРУ РЕВЬЮЕРОВ ХЕХЕХЕ 🚨",
            '<a href="https://vas3k.club/">Вернуться на главную</a>',  # plain text
        ],
    }


class Halloween(AnticBase):
    name = "halloween"
    type = "common"
    date = (10, 31)
    duration = 1
    global_cooldown = 1 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "skull", "label": "Напугать!"}
    notifications = [
        "**БУУУУ** 👻\n\nВы все были напуганы {sender}. С хэллоуином!",
        "{sender} подкинул сюда пауков. Ну а что вы хотели, сегодня можно.\n\n🕷️🕷️🕷️🕷️🕷️",
        "🕸️🕸️🕸️🕸️🕸️🕸️\nЧто это там за паутиной?\n🕸️🕸️🕸️\n\nЭто {sender}"
        " поздравляет всех с хэллоуином! 🎃",
        "Самое время пить тыквенный сок. Вон, {sender} принёс тыкв:\n\n🎃🎃🎃🎃🎃🎃",
        "- Тук-тук.\n- Кто там?\n- Это {sender}. Продление подписки или жизнь! 👻",
        "🦇🦇🦇🦇\n{sender} показывает на летающих мышей, что кружат над чатом!"
        "\nХотя, если присмотреться, это летучие червячки!\nС хэллоуином! 🎃\n\n🪱🪱🪱🪱",
        "Давайте бросим кости! 🎲🎲\nУ {sender} выпало...\n🦴🦴🦴🦴\n\nВидимо, мы не"
        " совсем правильно объяснились. кидать нужно было дайсы.\nЧто ж, с хэллоуином! 🎃",
        "Слышите этот истошный крик? Нет, ничего страшного, это всего лищь {sender}"
        " поздравляет всех с хэллоуином! 🎃",
        "Ой, свет моргнул, и тут появился зомби! 🧟\nА нет, это {sender} в страшном"
        "наряде пришёл всех поздравить с хэллоуином! 🎃",
        "Бу! 💀\n{sender} решил поздравить всех с хэллоуином! 🎃",
        "{sender} решил напугать чат 🎃\n\n_- На последней таске я накинул ещё пару"
        " требований. Кстати, овнер попросил задеплоить послезавтра._ 🧑🏻‍💻",
        "{sender} _пишет в рабочий чат:_\nДавайте перепишем всё на новом фреймворке 🧑🏻‍💻"
        "\n\nЛадно, это был байт. С хэллоуином! 🎃",
    ]
    success_messages = {
        "title": "Хехехе, чат напуган 🎃",
        "message_texts": [
            "**БУУУУ** 👻\n\nИ вы теперь напуганы.",
            "А вы задумывались, почему тыквенный спас ассоциируют со всякими пугалками? 🤔",
            "Но не переживайте, они всё понимают 🍁",
        ],
    }


class CoffeesDay(AnticBase):
    name = "coffees_day"
    type = "common"
    date = (10, 1)
    duration = 1
    global_cooldown = 4 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "mug-hot", "label": "Накофеинить!"}
    notifications = [
        "{sender} _решил напомнить, что сегодня день кофе, и надо его пить! ☕",
        "_В честь дня кофе_ {sender} _подкинул немного в чат. Разбирайте:_\n\n☕☕☕☕☕☕",
        "_Сегодня день кофе, и_ {sender} _напоминает: выпей ещё чашечку._",
        "_Нужно раздуплиться? Как вовремя, что сегодня день кофе, и_ {sender} _советует выпить чашечку._",
        "_Чат, внимание: в день кофе вам нельзя прекращать его пить, и как раз_ {sender}"
        " _принёс новую чашку_ ☕",
        "_Сегодня_ {sender} _крайне бодр. Настолько, что в честь Дня кофе принёс пару чашек сюда ☕☕_",
        "_По всяким интернет-версиям, кофе спасает от головоболезней._ {sender} _им, конечно,"
        " не верит, но что сегодня День кофе, напоминает._ ☕",
    ]
    success_messages = {
        "title": "Кофе в процессе доставки 🐌",
        "message_texts": [
            "Чат можно было и пожалеть, там и так уже все от кофетрясутся! ☕",
            "Самое время лечь поспать 😴",
            "Теперь они немного более кофеинезированы ☕",
        ],
    }


class WesternChristmas(AnticBase):
    name = "western_christmas"
    type = "common"
    date = (12, 25)
    duration = 2
    global_cooldown = 2 * HOUR
    user_cooldown = duration * DAY

    link = {"icon": "gift", "label": "Дать подарок!"}
    notifications = [
        "{sender} поздравляет всех с рождеством! 🎄",
        "{sender} закидывает всем вайба Рождества! 🔔",
        "{sender} желает всем провести это Рождество с теплотой и уютом! 🌟",
        "{sender} желает всем гармонии и тепла в Рождество! ✨",
        "{sender} отправляет всем немного рождественского уюта! ☃️",
        "{sender} делится рождественским настроением со всеми! ❄️",
        "{sender} желаем всем самую большую ёлку на Рождество! 🎄",
        "{sender} вешает всем подарки на ёлку и кладёт игрушки под неё! 🎁",
        "{sender} напоминает включить гирлянды, чтобы Рождество прошло уютно! 🕯️",
        "{sender} разливает всем рождественского глинтвейна! 🍷",
        "{sender} раздаёт всем хлеба и вина: сегодня Рождество! 🔔",
        "{sender} пытается призвать Санту и поздравляет всех с Рождеством! 🎅",
    ]
    success_messages = {
        "title": "Чат поздравлен 💫",
        "message_texts": [
            "Заваривай чашечку глинтвейна и залетай с ним в [Бар](https://vas3k.club/room/bar/chat/) 🥃",
            "И тебя с праздником! 🎄",
            "Он родился. А что произошло дальше, мы с вами сейчас и узнаем 🐙",
        ],
    }


class WesternChristmasPrivate(AnticBase):
    name = "western_christmas_private"
    type = "private"
    date = (12, 25)
    duration = 2
    user_cooldown = 30 * MIN

    link = {"icon": "🎁", "label": "Поздравить с рождеством"}
    notifications = [
        "{sender} поздравляет тебя с Рождеством! 🎅🏻",
        "{sender} шлёт тебе тёплые рождественские пожелания! 🎁",
        "{sender} передал тебе частичку рождественского настроения! 🎄",
        "{sender} делится с тобой рождественским вайбом, так что теперь вайбуй! ✨",
        "Лови снежок! ☃️\nЭто {sender} таким образом поздравляет тебя с рождеством.",
        "🎁\nЧто это? Подарок? Открывай!\nОго, это {sender} передаёт поздравления с Рождеством!",
        "Держи рождественского уюта, тебе его тебе передал {sender} 🎇",
        "Слышишь? Чувствуешь? {sender} поздравляет тебя с Рождеством! 🔔",
    ]
    success_messages = {
        "title": "Поздравление улетело 💫",
        "message_texts": [
            "А что это ещё летит? А, это вайб на подлёте! Вот он: ✨✨✨",
            "Мы передадим его с рождественскими эльфами 🧝🏻",
            "Оно попало прямо под ёлочку 🎁",
            "Что ж, а теперь пора праздновать! 🍾",
        ],
    }


class UnexpectedDay(AnticBase):
    name = "unexpected_day"
    type = "bottom_link"
    date = (random.randint(1, 12), random.randint(1, 28))
    duration = random.randint(1, 3)
    global_cooldown = duration * DAY

    link = {"icon": "", "label": "Ничего подозрительного тут"}
    notifications = [
        "{sender} _заметил то, что старалось быть незамеченным._",
        "_Аномалия, обнаруженная_ {sender}_, передана в профильный отдел анализа аномалий._",
        "_Благодаря_ {sender} _стало ясно, что всё не так просто._",
        "_В ходе наблюдения_ {sender} _были зафиксированы отклонения от штатного режима._",
        "_Обнаруженное_ {sender} _отправлено на дальнейшее изучение._",
        "_По информации_ {sender}_, происходит некое несоответствие установленным параметрам._",
        "_Сигнал, поступивший от_ {sender}_, классифицирован как нестандартный._",
        "_Согласно наблюдениям_ {sender}_, стабильность нестабильна._",
    ]
    success_messages = {
        "title": "Об этом инциденте теперь знают все 👾",
        "message_texts": [
            "Дальше ситуация находится под контролем 🇦🇶️",
            "Запущен внутренний протокол реагирования 📡",
            "Материалы переданы в профильные агентства 🛸",
            "Ответственные подразделения уже уведомлены 🕵️🏻",
        ],
    }


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
