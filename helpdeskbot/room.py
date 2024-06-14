from rooms.models import Room


def get_rooms() -> list[Room]:
    return list(Room.objects\
                .filter(is_visible=True, chat_id__isnull=False)\
                .order_by("index")
                .all())
