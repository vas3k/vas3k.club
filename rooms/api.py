from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from rooms.models import Room, RoomSubscription, RoomMuted


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def toggle_room_subscription(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)

    if request.method == "POST":
        RoomSubscription.subscribe(user=request.me, room=room)
    elif request.method == "DELETE":
        RoomSubscription.unsubscribe(user=request.me, room=room)

    is_subscribed = RoomSubscription.is_subscribed(user=request.me, room=room)

    return {"status": "created" if is_subscribed else "deleted", "is_subscribed": is_subscribed}


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def toggle_room_mute(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)

    if request.method == "POST":
        RoomMuted.mute(user=request.me, room=room)
    elif request.method == "DELETE":
        RoomMuted.unmute(user=request.me, room=room)

    is_muted = RoomMuted.is_muted(user=request.me, room=room)

    return {"status": "created" if is_muted else "deleted", "is_muted": is_muted}
