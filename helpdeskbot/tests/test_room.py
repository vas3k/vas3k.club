from django.test import TestCase

from helpdeskbot.room import get_rooms
from misc.models import NetworkGroup
from rooms.models import Room


class TestHelpdeskBotRooms(TestCase):
    def setUp(self):
        self.group_geo = NetworkGroup.objects.create(code="geo", title="Geo")
        self.group_other = NetworkGroup.objects.create(code="other", title="Other")

    def test_get_rooms_filters_by_group_and_chat_id(self):
        Room.objects.create(
            slug="included",
            title="Included",
            color="#111111",
            chat_id="100",
            network_group=self.group_geo,
        )
        Room.objects.create(
            slug="excluded_no_chat",
            title="Excluded No Chat",
            color="#111111",
            chat_id=None,
            network_group=self.group_geo,
        )
        Room.objects.create(
            slug="excluded_group",
            title="Excluded Group",
            color="#111111",
            chat_id="101",
            network_group=self.group_other,
        )

        rooms = list(get_rooms())

        self.assertEqual([room.slug for room in rooms], ["included"])
