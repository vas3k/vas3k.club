class ClubException(Exception):
    default_code = "error"
    default_title = "Что-то пошло не так"
    default_message = "Никто не знает что произошло :("

    def __init__(self, code=None, title=None, message=None, data=None):
        self.code = code or self.default_code
        self.title = title or self.default_title
        self.message = message or self.default_message
        self.data = data or {}


class BadRequest(ClubException):
    default_code = "bad-request"
    default_title = "Неправильный параметр запроса"
    default_message = "Что-то сломалось"


class NotFound(ClubException):
    default_code = "not-found"
    default_title = "Не найдено"
    default_message = ""


class AccessDenied(ClubException):
    default_code = "access-forbidden"
    default_title = "Вам сюда нельзя"
    default_message = "Атата"


class RateLimitException(ClubException):
    default_code = "rate-limit"
    default_title = "Вы создали слишком много постов или комментов сегодня"
    default_message = "Пожалуйста, остановитесь"


class ContentDuplicated(ClubException):
    default_code = "duplicated-content"
    default_title = "Обнаружен дубликат!"
    default_message = "Кажется, вы пытаетесь опубликовать то же самое повторно. " \
                      "Проверьте всё ли в порядке."


class InsufficientFunds(ClubException):
    default_code = "insufficient-funds"
    default_title = "Недостаточно средств"


class URLParsingException(ClubException):
    default_code = "url-parser-exception"
    default_title = "Не удалось распарсить URL"
    default_message = ""


class InvalidCode(ClubException):
    default_code = "invalid-code"
    default_title = "Вы ввели неправильный код"
    default_message = "Введите или запросите его еще раз. Через несколько неправильных попыток коды удаляются"


class ApiInsufficientFunds(ClubException):
    default_code = "api-insufficient-funds"
    default_title = "Недостаточно средств"


class ApiException(ClubException):
    default_message = None


class ApiBadRequest(ClubException):
    default_code = "bad-request"
    default_title = "Неправильный параметр запроса"


class ApiAuthRequired(ApiException):
    default_code = "api-auth-required"
    default_title = "Auth Required"


class ApiAccessDenied(ApiException):
    default_code = "api-access-denied"
    default_title = "Access Denied"

