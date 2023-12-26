from club.exceptions import ClubException


class AuthException(ClubException):
    pass


class PatreonException(AuthException):
    pass
