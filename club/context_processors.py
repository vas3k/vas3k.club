from django.conf import settings

from common.data.expertise import EXPERTISE


def settings_processor(request):
    return {
        "settings": settings
    }


def data_processor(request):
    return {
        "global_data": {
            "expertise": EXPERTISE,
        }
    }
