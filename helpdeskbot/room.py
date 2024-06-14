from rooms.models import Room


def get_rooms():
    return list(Room.objects\
                .filter(is_visible=True, chat_id__isnull=False)\
                .order_by("index")
                .all())
