from rooms.models import Room


def get_rooms():
    return Room.visible_rooms().filter(
        chat_id__isnull=False,
        network_group_id__in=["geo", "chats", "prof"],
    ).order_by("network_group_id", "title")
