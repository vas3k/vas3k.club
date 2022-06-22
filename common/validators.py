from django.core.exceptions import ValidationError

from common import regexp


def validate_has_spaces(value):
    match = regexp.NO_SPACES_RE.match(value)
    if match:
        raise ValidationError("Нет ни одного пробела")


def validate_is_russian(value):
    match = regexp.NO_RU_LETTERS_RE.match(value)
    if match:
        raise ValidationError("Текст должен содержать русский язык")


def validate_repetitions(value):
    match = regexp.REPETITIONS_RE.search(value)
    if match:
        raise ValidationError("Слишком много дублирования")
