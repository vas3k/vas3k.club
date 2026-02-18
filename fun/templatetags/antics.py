from django import template
from fun.antics import ANTICS

register = template.Library()


@register.filter
def get_current_antics(antic_type: str) -> list[dict]:
    return [
        antic | {"name": name}
        for (name, antic) in ANTICS.items()
        if antic["type"] == antic_type
    ]
