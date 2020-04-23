from datetime import datetime


def first_day_of_next_month(dt):
    if dt.month == 12:
        return datetime(year=dt.year + 1, month=1, day=1, tzinfo=dt.tzinfo)
    else:
        return datetime(year=dt.year, month=dt.month + 1, day=1, tzinfo=dt.tzinfo)
