from rooms.models import Room


def get_rooms():
    return Room.objects.filter(
        is_visible=True,
        chat_id__isnull=False,
        network_group_id__in=["geo", "chats", "prof"]
    ).order_by("network_group_id", "title").all()
