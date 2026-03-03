import re
import requests
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
