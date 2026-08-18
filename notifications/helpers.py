import hashlib
import hmac
import time

from django.conf import settings


def generate_notification_token(user) -> str:
    timestamp = str(int(time.time()))
    return f"{timestamp}.{_sign(user.id, timestamp)}"


def verify_notification_token(user, token: str) -> bool:
    try:
        timestamp, signature = token.split(".", 1)
    except ValueError:
        return False

    if not timestamp.isdigit():
        return False

    return hmac.compare_digest(_sign(user.id, timestamp), signature)


def _sign(user_id, timestamp: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"notif:{user_id}:{timestamp}".encode(),
        hashlib.sha256,
    ).hexdigest()
