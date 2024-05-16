from django.conf import settings

from club import features


def settings_processor(request):
    return {
        "settings": settings
    }


def features_processor(request):
    return {"features": features}
