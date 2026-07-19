from django.core.cache import cache

from authn.models.session import Session

AUTH_TOKEN_CACHE_TIMEOUT = 3 * 60  # seconds


def auth_token_cache_key(token: str) -> str:
    return f"auth:token:{token}"


def clear_auth_token_cache(token: str | None) -> None:
    if token:
        cache.delete(auth_token_cache_key(token))


def clear_auth_token_cache_for_user(user) -> None:
    tokens = list(Session.objects.filter(user=user).values_list("token", flat=True))
    if tokens:
        cache.delete_many([auth_token_cache_key(token) for token in tokens])
