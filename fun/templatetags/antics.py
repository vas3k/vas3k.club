from typing import Type
from django import template

from fun.antics import ANTICS, AnticBase
from users.models.user import User

register = template.Library()


@register.filter
def get_current_antics(
    antic_type: str, sender: User | None = None
) -> list[Type[AnticBase]]:
    if not sender:
        return []
    return list(filter(lambda a: a.is_displayable(antic_type, sender), ANTICS))
