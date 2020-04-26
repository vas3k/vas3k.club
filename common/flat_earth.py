import logging
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache
from requests import RequestException

log = logging.getLogger(__name__)


def parse_horoscope():
    if not settings.SIMPLEPARSER_API_KEY:
        return {}

    moon_phase = cache.get("moon_phase")
    if not moon_phase:
        try:
            moon_phase = requests.get(
                f"https://simplescraper.io/api/y4gLaoFV8m9cnOMXk4JB"
                f"?apikey={settings.SIMPLEPARSER_API_KEY}&offset=0&limit=20"
            ).json()
            cache.set("moon_phase", moon_phase, timeout=60 * 60)
        except RequestException as ex:
            log.exception(f"Horoscope error: {ex}")
            return {}

    return {
        "club_day": (datetime.utcnow() - settings.LAUNCH_DATE).days,
        "phase_num": _get_by_index(moon_phase, "moon_phase", 1),
        "phase_sign": _get_by_index(moon_phase, "moon_phase", 2),
        "phase_description": _get_by_index(moon_phase, "moon_description", 11)[:-18],
    }


def _get_by_index(moon_phase, key, index):
    try:
        return [mp[key] for mp in moon_phase["data"] if mp["index"] == index][0]
    except (KeyError, IndexError):
        return ""
