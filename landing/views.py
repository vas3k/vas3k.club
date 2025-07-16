from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import render

from users.models.user import User


def landing(request):
    stats = cache.get("landing_stats")
    if not stats:
        stats = {
            "users": User.registered_members().count(),
            "countries": User.registered_members().values("country")
            .annotate(total=Count("country")).order_by().count() + 1,
        }
        cache.set("landing_stats", stats, settings.LANDING_CACHE_TIMEOUT)

    return render(request, "landing.html", {
        "stats": stats
    })
