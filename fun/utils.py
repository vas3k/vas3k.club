import re
import requests
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from bs4 import BeautifulSoup
from django.core.cache import cache


BANEKS_URL = "https://baneks.ru/random"


def get_new_banek() -> str:
    res = requests.get(BANEKS_URL)
    soup = BeautifulSoup(res.text, "lxml")
    banek = soup.select_one("body > main > section > article > p")
    return re.sub("\s*\n\s*", "\n", banek.get_text(separator="\n"))


def get_dayly_banek() -> str:
    banek = cache.get("fun:dayly_banek")
    if not banek:
        for _ in range(3):
            try:
                banek = get_new_banek()
                break
            except:
                pass
        else:
            banek = "_... решил не отзываться на запрос чата._"
        cache.set("fun:dayly_banek", banek, timeout=60 * 60 * 24)
    return banek


def check_today_for_antic(month: int, day: int, duration: int = 1) -> bool:
    antic_start = date(2000, month, day)
    antic_end = antic_start + timedelta(days=duration)
    year_td = relativedelta(years=1)
    today = date.today().replace(year=2000)
    return (
        antic_start <= today < antic_end
        or (antic_start - year_td) <= today < (antic_end - year_td)  # new year
    )
