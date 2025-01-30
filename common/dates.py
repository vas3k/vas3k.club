import random
from datetime import datetime, timedelta


def random_date_in_range(start_date: datetime, end_date: datetime) -> datetime:
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)
