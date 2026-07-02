from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from authn.decorators.auth import require_auth
from rooms.models import Room, RoomSubscription, RoomMuted
from users.models.user import User


@require_auth
def list_rooms(request):
    rooms = list(Room.visible_rooms().order_by("-last_activity_at"))

    # prefetch admins for all rooms (speed up)
    admin_slugs = {
        slug
        for room in rooms
        for slug in room.admins
    }
    if admin_slugs:
        users_by_slug = User.objects.in_bulk(admin_slugs, field_name="slug")
        for room in rooms:
            room._admins_with_details = [
                users_by_slug[slug]
                for slug in room.admins
                if slug in users_by_slug
            ]
    else:
        for room in rooms:
            room._admins_with_details = []

    return render(request, "rooms/list_rooms.html", {
        "rooms": rooms,
    })


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
