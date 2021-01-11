from itertools import chain

EXPERTISE = [
    ("Хард-скиллы", [
        ("frontend", "Фронтенд"),
        ("backend", "Бекенд"),
        ("mobile", "Мобильная разработка"),
        ("machine-learning", "Машинное Обучение"),
        ("data", "Данные и аналитика"),
        ("infra", "Инфраструктура"),
        ("crypto", "Крипта"),
        ("qa", "QA"),
        ("devops", "DevOps"),
        ("hardware", "Хардварь"),
        ("imaging", "Компьютерное зрение"),
        ("nlp", "NLP"),
        ("iot", "IoT"),
        ("embedded", "Встраиваемые системы"),
        ("ux", "UX/UI"),
        ("pm", "Продакт-менеджмент"),
        ("security", "Безопасность"),
        ("marketing", "Маркетинг"),
        ("video", "Видео-продакшен"),
        ("audio", "Аудио"),
        ("copywriting", "Копирайтинг"),
        ("design", "Дизайн"),
        ("science", "Наука"),
        ("business", "Бизнес"),
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
    ("Языки", [
        ("python", "Python"),
        ("java", "Java"),
        ("javascript", "JavaScript"),
        ("go", "Go"),
        ("php", "PHP"),
        ("ruby", "Ruby"),
        ("swift", "Swift"),
        ("cplus", "C/C++"),
        ("csharp", "C#"),
    ])
]


EXPERTISE_FLAT_MAP = dict(chain.from_iterable(items for _, items in EXPERTISE))
