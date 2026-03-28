from authn.decorators.api import api
from rooms.models import Room


@api(require_auth=True)
def api_rooms(request):
    rooms = Room.objects.filter(is_visible=True)
    return {
        "rooms": [room.to_dict() for room in rooms]
    }
