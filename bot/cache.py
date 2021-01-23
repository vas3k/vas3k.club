from django.core.cache import cache

from users.models.user import User


def cached_telegram_users():
    club_users = cache.get("bot:telegram_user_ids") or []
    if not club_users:
        club_users = User.objects \
            .filter(telegram_id__isnull=False, moderation_status=User.MODERATION_STATUS_APPROVED) \
            .values_list("telegram_id", flat=True)
        cache.set("bot:telegram_user_ids", list(club_users), 5 * 60)
    return club_users


def flush_users_cache():
    cache.delete("bot:telegram_user_ids")
