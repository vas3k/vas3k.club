import json
import logging
from django.utils.encoding import *
import requests

log = logging.getLogger()


def geocode_find_city_id_by_name(country, city):
    url = f"https://nominatim.openstreetmap.org/search?city={escape_uri_path(city)}&country={escape_uri_path(country)}&format=json&accept-language=ru,en&limit=1"
    response = requests.get(url, timeout=2, headers={'User-Agent': 'vas3k.club user location club@vas3k.club'})
    j = json.loads(response.content)
    if len(j) >= 1 and float(j[0]["importance"]) > 0.35:
        return j[0]["display_name"], j[0]["osm_id"]
    return (None, None)
