import random


ANTICS = {
    "new_year": {
        "type": "common",
        "date": (12, 31),
        "duration": 2,
        "link": {
            "icon": "gifts",
            "label": "Навайбить!",
        },
    },
    "new_year_private": {
        "type": "private",
        "date": (12, 31),
        "duration": 2,
        "link": {
            "icon": "🎅🏻",
            "label": "Поздравить с Новым Годом",
        },
    },
    "valentine_common": {
        "type": "common",
        "date": (2, 14),
        "duration": 1,
        "link": {
            "icon": "heart",
            "label": "Выдать любовь!",
        },
    },
    "valentine": {
        "type": "private",
        "date": (2, 14),
        "duration": 1,
        "link": {
            "icon": "💝",
            "label": "Отправить валентинку",
        },
    },
    "valentine_anonymous": {
        "type": "private",
        "date": (2, 14),
        "duration": 1,
        "link": {
            "icon": "💖",
            "label": "Отправить анонимку",
        },
    },
    "leap_day": {
        "type": "common",
        "date": (2, 29),
        "duration": 1,
        "link": {
            "icon": "calendar-alt",
            "label": "Зафиксировать!",
        },
    },
    "fools_day": {
        "type": "common",
        "date": (4, 1),
        "duration": 1,
        "link": {
            "icon": "laugh",
            "label": "Наклоунадничать!",
        },
    },
    "cosmonautics_day": {
        "type": "common",
        "date": (4, 12),
        "duration": 1,
        "link": {
            "icon": "rocket",
            "label": "Стартовать!",
        },
    },
    "club_birthday": {
        "type": "common",
        "date": (4, 15),
        "duration": 1,
        "link": {
            "icon": "birthday-cake",
            "label": "Поздравить!",
        },
    },
    "summer_solstice": {
        "type": "common",
        "date": (6, 21),
        "duration": 1,
        "link": {
            "icon": "sun",
            "label": "Подсветить!",
        },
    },
    "friends_day": {
        "type": "common",
        "date": (7, 30),
        "duration": 1,
        "link": {
            "icon": "smile",
            "label": "Подружиться!",
        },
    },
    "friends_day_private": {
        "type": "private",
        "date": (7, 30),
        "duration": 1,
        "link": {
            "icon": "👯‍♂️",
            "label": "Признаться в дружбе",
        },
    },
    "cats_day": {
        "type": "common",
        "date": (8, 8),
        "duration": 1,
        "link": {
            "icon": "cat",
            "label": "Помурлыкать!",
        },
    },
    "cats_day_private": {
        "type": "private",
        "date": (8, 8),
        "duration": 1,
        "link": {
            "icon": "😺",
            "label": "Обозвать котиком",
        },
    },
    "testers_day": {
        "type": "common",
        "date": (9, 9),
        "duration": 1,
        "link": {
            "icon": "bug",
            "label": "Создать баги!",
        },
    },
    "halloween": {
        "type": "common",
        "date": (10, 31),
        "duration": 1,
        "link": {
            "icon": "skull",
            "label": "Напугать!",
        },
    },
    "coffees_day": {
        "type": "common",
        "date": (10, 1),
        "duration": 1,
        "link": {
            "icon": "mug-hot",
            "label": "Накофеинить!",
        },
    },
    "western_christmas": {
        "type": "common",
        "date": (12, 25),
        "duration": 2,
        "link": {
            "icon": "gift",
            "label": "Дать подарок!",
        },
    },
    "western_christmas_private": {
        "type": "private",
        "date": (12, 25),
        "duration": 2,
        "link": {
            "icon": "🎁",
            "label": "Поздравить с рождеством",
        },
    },
    # ===
    "unexpected_day": {
        "type": "unexpected_day",
        "date": (random.randint(1, 12), random.randint(1, 28)),
        "duration": random.randint(1, 3),
        "link": {
            "icon": "",
            "label": "Ничего подозрительного тут",
        },
    },
    "miss": {
        "type": "miss",
        "date": (1, 1),
        "duration": 1,
        "link": {
            "icon": "",
            "label": "",
        },
    },
}
