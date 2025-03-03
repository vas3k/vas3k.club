from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.utils.translation import gettext as _

from posts.helpers import ORDERING_TOP, ORDERING_TOP_YEAR, ORDERING_TOP_MONTH, ORDERING_TOP_WEEK
from rooms.models import Room

ORDERING_LAST_MONTHS = 12


def rooms(request):
    rooms = Room.objects.filter(is_visible=True, is_open_for_posting=True).order_by("-last_activity_at").all()
    return {
        "rooms": rooms,
        "rooms_map": {room.slug: room for room in rooms},
    }


def ordering(request):
    return {
        "feed_ordering_options": [
            {
                "text": "вообще",
                "value": ORDERING_TOP,
            },
            {
                "text": "за год",
                "value": ORDERING_TOP_YEAR,
            },
            {
                "text": "за месяц",
                "value": ORDERING_TOP_MONTH,
            },
            {
                "text": "за неделю",
                "value": ORDERING_TOP_WEEK
            }
        ],
        "feed_ordering_years": [
            {
                "text": "за 365 дней",
                "value": ORDERING_TOP_YEAR,
            },
            *[
                {
                    "text": f"{year}",
                    "value": f"{ORDERING_TOP_YEAR}:{year}",
                } for year in range(datetime.utcnow().year, settings.LAUNCH_DATE.year, -1)
            ]
        ],
        "feed_ordering_months": [
            {
                "text": "за 30 дней",
                "value": ORDERING_TOP_MONTH,
            },
            *[
                {
                    "text": f"{_(d.strftime("%B"))} {d.year}".lower(),
                    "value": f"{ORDERING_TOP_MONTH}:{d.year}-{d.month}",
                } for d in [
                    datetime.utcnow().replace(day=1) - relativedelta(months=i)
                    for i in range(ORDERING_LAST_MONTHS)
                ]
            ]
        ]
    }
