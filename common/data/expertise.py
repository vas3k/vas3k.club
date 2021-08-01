from itertools import chain

EXPERTISE = [
    ("Хард-скиллы", [
        ("seo", "Seo"),
        ("mediabuying", "Медиабаинг"),
        ("marketing", "Маркетинг"),
        ("target", "Таргет"),
        ("copywriting", "Копирайтинг"),
        ("context", "Контекстная реклама"),
        ("dev", "Разработка"),
        ("design", "Дизайн"),
        ("data", "Данные и аналитика"),
        ("crypto", "Крипта"),
        ("project", "Проджект менеджмент"),
        ("product", "Продакт менеджмент"),
        ("bisdev", "БизДев"),
    ]),
    ("Софт-скиллы", [
        ("hire", "Найм людей"),
        ("lead", "Управление командами"),
        ("critical", "Критическое мышление"),
        ("rationality", "Рациональность"),
        ("conflicts", "Решение конфликтов"),
        ("coaching", "Менторинг"),
        ("public-speaking", "Публичные выступления"),
        ("planning", "Планирование"),
        ("ethics", "Этика"),
    ]),
    ("Вертикаль", [
        ("gambling", "Гемблинг"),
        ("betting", "Беттинг"),
        ("crypto", "Крипта"),
        ("nutra", "Нутра"),
        ("leadgen", "Лидген"),
        ("goods", "Товарка"),
        ("fintech", "Финтех"),
        ("adult", "Адалт"),
        ("dating", "Дейтинг"),
        ("client", "Клиентское"),
    ])
]


EXPERTISE_FLAT_MAP = dict(chain.from_iterable(items for _, items in EXPERTISE))
