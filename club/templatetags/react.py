import json

from django import template
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def react(component_name, **props):
    converted_props = {}

    for key, value in props.items():
        first, *rest = key.split("_")
        converted_props[first + "".join(word.capitalize() for word in rest)] = value

    return format_html(
        '<div data-island="{}" data-props="{}"></div>',
        component_name,
        json.dumps(converted_props, cls=DjangoJSONEncoder),
    )


@register.filter
def coauthors_options(users):
    return [{"slug": user.slug, "full_name": user.full_name, "avatar": user.get_avatar()} for user in users]


@register.filter
def room_options(rooms):
    return [{"slug": room.slug, "title": room.title, "emoji": room.emoji(), "image": room.image} for room in rooms]
