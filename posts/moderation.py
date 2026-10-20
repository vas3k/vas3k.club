from enum import Enum


class PostRejectReason(Enum):
    ad = "ad"
    bias = "bias"
    chat = "chat"
    design = "design"
    draft = "draft"
    duplicate = "duplicate"
    dyor = "dyor"
    false_dilemma = "false_dilemma"
    github = "github"
    hot = "hot"
    inside = "inside"
    self = "self"
    title = "title"
    tldr = "tldr"
    tldr_link = "tldr_link"
    value = "value"


REJECT_POST_REASONS = {
    "post": [
        ("title", "Плохой заголовок"),
        ("inside", "Мало личного опыта"),
        ("value", "Не ясна польза Клубу"),
        ("design", "Плохо оформлен"),
        # TODO: ИИ слоп
    ],
    "event": [
        ("title", "Плохой заголовок"),
        ("design", "Ивент недооформлен"),
    ],
    "guide": [
        ("title", "Плохой заголовок"),
        ("design", "Гайд недооформлен"),
    ],
    "thread": [
        ("title", "Плохой заголовок"),
        ("design", "Тред недооформлен"),
        ("duplicate", "Дубликат"),
    ],
    "question": [
        ("title", "Плохой заголовок"),
        ("chat", "Лучше в чат"),
        ("dyor", "Нет рисёрча, коротко"),
        ("hot", "Провокация/срач"),
        ("duplicate", "Дубликат"),
    ],
    "link": [
        ("tldr_link", "Короткое описание"),
        ("self", "Ссылка на себя"),
        ("value", "Бесполезно/непонятно"),
    ],
    "battle": [
        ("hot", "Срач"),
        ("false_dilemma", "Ложная дилемма"),
        ("duplicate", "Дубликат"),
        ("bias", "Предвзят к одному варианту"),
    ],
    "project": [
        ("design", "Проект недооформлен"),
        ("ad", "Похоже на рекламу"),
        ("inside", "Нет инсайдов и опыта"),
        # TODO: ИИ слоп-проект
    ],
    "request": [
        ("title", "Плохой заголовок"),
        ("tldr", "Мало описания"),
        ("duplicate", "Дубликат"),
    ],
}
