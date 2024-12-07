from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from authn.decorators.auth import require_auth
from rooms.models import Room, RoomSubscription, RoomMuted


@require_auth
def list_rooms(request):
    return render(request, "rooms/list_rooms.html")


@require_auth
def redirect_to_room_chat(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)
    if room.url:
        return redirect(room.url, permanent=False)
    elif room.chat_url:
        return redirect(room.chat_url, permanent=False)
    else:
        raise Http404()


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_room_subscription(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)

    subscription, is_created = RoomSubscription.subscribe(
        user=request.me,
        room=room,
    )

    if not is_created:
        # already exist? remove it
        RoomSubscription.unsubscribe(
            user=request.me,
            room=room,
        )

    return {
        "status": "created" if is_created else "deleted"
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def toggle_room_mute(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)

    mute, is_created = RoomMuted.mute(
        user=request.me,
        room=room,
    )

    if not is_created:
        RoomMuted.unmute(
            user=request.me,
            room=room,
        )

    return {
        "status": "created" if is_created else "deleted"
    }
