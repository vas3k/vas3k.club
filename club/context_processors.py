from django.conf import settings

from club import features
from godmode.models import ClubSettings


class UniversalSettings:
    def __getattr__(self, item, default=None):
        if hasattr(settings, item):
            return getattr(settings, item, default)
        return ClubSettings.get(item, default)


def settings_processor(request):
    return {
        "settings": UniversalSettings()
    }


def features_processor(request):
    return {
        "features": features
    }
