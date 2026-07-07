from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from authn.decorators.auth import require_auth
from common.pagination import paginate
from rooms.models import Room, RoomSubscription, RoomMuted
from users.models.user import User


@require_auth
def list_rooms(request):
    rooms = paginate(request, Room.visible_rooms().order_by("-last_activity_at"))
    room_slugs = [room.slug for room in rooms]

    # prefetch admins for rooms on the current page
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

    if room_slugs:
        subscribed_room_slugs = set(RoomSubscription.objects.filter(
            user=request.me,
            room_id__in=room_slugs,
        ).values_list("room_id", flat=True))
        muted_room_slugs = set(RoomMuted.objects.filter(
            user=request.me,
            room_id__in=room_slugs,
        ).values_list("room_id", flat=True))
    else:
        subscribed_room_slugs = set()
        muted_room_slugs = set()

    for room in rooms:
        room.is_subscribed_by_me = room.slug in subscribed_room_slugs
        room.is_muted_by_me = room.slug in muted_room_slugs

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
