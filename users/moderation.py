from enum import Enum


class UserRejectReason(Enum):
    intro = "intro"
    data = "data"
    ai = "ai"
    aggression = "aggression"
    general = "general"
    name = "name"

