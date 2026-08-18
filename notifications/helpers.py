import hashlib
import hmac
import time

from django.conf import settings


def generate_notification_token(user) -> str:
    timestamp = str(int(time.time()))
    return f"{timestamp}.{_sign(user.secret_hash, timestamp)}"


def verify_notification_token(user, token: str) -> bool:
    try:
        timestamp, signature = token.split(".", 1)
    except ValueError:
        return False

    if not timestamp.isdigit():
        return False

    return hmac.compare_digest(_sign(user.secret_hash, timestamp), signature)


def _sign(secret_hash: str, timestamp: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"notif:{secret_hash}:{timestamp}".encode(),
        hashlib.sha256,
    ).hexdigest()
