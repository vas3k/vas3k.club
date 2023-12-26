from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from authn.decorators.auth import require_auth
from rooms.models import Room


@require_auth
def list_rooms(request):
    return render(request, "rooms/list_rooms.html")


@require_auth
def redirect_to_room_chat(request, room_slug):
    room = get_object_or_404(Room, slug=room_slug)
    if room.chat_url:
        return redirect(room.chat_url, permanent=False)
    elif room.url:
        return redirect(room.url, permanent=False)
    else:
        raise Http404()
