from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext

from debug.utils_for_tests import create_approved_user, login
from rooms.models import Room, RoomMuted, RoomSubscription


def create_room(slug, **kwargs):
    defaults = dict(
        title=slug,
        description=f"{slug} description",
        color="#333333",
        is_visible=True,
        is_open_for_posting=True,
    )
    defaults.update(kwargs)
    return Room.objects.create(slug=slug, **defaults)


class TestListRooms(TestCase):
    def setUp(self):
        self.user = create_approved_user("rooms_viewer")
        self.client = Client()
        login(self.client, self.user)

    def test_subscription_and_mute_state_with_bulk_queries(self):
        subscribed_room = create_room("subscribed-room")
        muted_room = create_room("muted-room")
        create_room("plain-room")

        RoomSubscription.objects.create(user=self.user, room=subscribed_room)
        RoomMuted.objects.create(user=self.user, room=muted_room)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/rooms/")

        self.assertEqual(response.status_code, 200)
        room_states = {
            room.slug: (room.is_subscribed_by_me, room.is_muted_by_me)
            for room in response.context["rooms"]
        }
        self.assertEqual(room_states, {
            "subscribed-room": (True, False),
            "muted-room": (False, True),
            "plain-room": (False, False),
        })

        subscription_queries = [
            query["sql"] for query in queries
            if "room_subscriptions" in query["sql"]
        ]
        muted_queries = [
            query["sql"] for query in queries
            if "room_muted" in query["sql"]
        ]

        self.assertEqual(len(subscription_queries), 1)
        self.assertEqual(len(muted_queries), 1)
