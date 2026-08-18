import hmac

from django.conf import settings
from django.core.signing import BadSignature, TimestampSigner


def generate_notification_token(user) -> str:
    return TimestampSigner(salt=user.secret_hash).sign(str(user.id))


def verify_notification_token(user, token: str) -> bool:
    try:
        unsigned = TimestampSigner(salt=user.secret_hash).unsign(
            token, max_age=settings.NOTIFICATION_TOKEN_EXPIRATION_TIMEDELTA
        )
        return hmac.compare_digest(unsigned, str(user.id))
    except (BadSignature, TypeError):
        return False
