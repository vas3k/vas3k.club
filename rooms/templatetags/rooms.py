from django import template

from rooms.models import RoomSubscription, RoomMuted

register = template.Library()


@register.filter
def is_room_subscribed(room, user):
    if not user or not room:
        return False
    return RoomSubscription.is_subscribed(user, room)


@register.filter
def is_room_muted(room, user):
    if not user or not room:
        return False
    return RoomMuted.is_muted(user, room)
