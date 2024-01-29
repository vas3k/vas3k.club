from rooms.models import Room


def get_rooms() -> list[Room]:
    return list(Room.objects.filter(is_visible=True).all())
