from rooms.models import Room


def rooms(request):
    rooms = Room.objects.filter(is_visible=True, is_open_for_posting=True).order_by("-last_activity_at").all()
    return {
        "rooms": rooms,
        "rooms_map": {room.slug: room for room in rooms},
    }
