import logging
from datetime import datetime

import requests
from django.conf import settings
from django.core.cache import cache
from django.utils.html import strip_tags
from bs4 import BeautifulSoup
from requests import RequestException

log = logging.getLogger(__name__)

MAGIC_URL = "https://www.life-moon.pp.ru/"


def parse_horoscope():
    moon_phase = cache.get("moon_phase")
    if not moon_phase:
        try:
            soup = BeautifulSoup(requests.get(MAGIC_URL).text, features="lxml")
        except RequestException:
            return {
                "club_day": (datetime.utcnow() - settings.LAUNCH_DATE).days,
                "phase_num": "",
                "phase_sign": "",
                "phase_description": "",
            }

        moon_phase = {}

        horoscope = soup.select("body > section > section > article > div.l-box > p:nth-child(3)")
        moon_phase["phase_description"] = strip_tags(horoscope[0])[:-18] if horoscope else ""

        phase_num = soup.select("table.moon-events-table td.text-left > ul > li:nth-child(1)")
        moon_phase["phase_num"] = strip_tags(phase_num[0]) if phase_num else ""

        phase_sign = soup.select("table.moon-events-table tr:nth-child(2) > td.text-left > ul > li > a")
        moon_phase["phase_sign"] = strip_tags(phase_sign[0]) if phase_sign else ""
        cache.set("moon_phase", moon_phase, timeout=60 * 60)

    return {
        "club_day": (datetime.utcnow() - settings.LAUNCH_DATE).days,
        "phase_num": moon_phase["phase_num"],
        "phase_sign": moon_phase["phase_sign"],
        "phase_description": moon_phase["phase_description"],
    }
