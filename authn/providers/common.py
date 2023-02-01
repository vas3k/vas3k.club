from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class Platform(str, Enum):
    patreon = "patreon"


@dataclass
class Membership:
    platform: Platform
    user_id: str
    full_name: str
    email: str
    image: Optional[str]
    started_at: Optional[datetime]
    charged_at: Optional[datetime]
    expires_at: Optional[datetime]
    lifetime_support_cents: Optional[int]
    currently_entitled_amount_cents: int
