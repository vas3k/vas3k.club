from datetime import datetime, timedelta

from django.db import connection
from django.test import Client, TestCase
from django.test.utils import CaptureQueriesContext

from authn.models.session import Session
from rooms.models import Room, RoomMuted, RoomSubscription
from users.models.user import User


def _create_user(slug):
    return User.objects.create(
        slug=slug,
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.utcnow() - timedelta(days=5),
        membership_expires_at=datetime.utcnow() + timedelta(days=365),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )


def _create_room(slug, **kwargs):
    defaults = dict(
        title=slug,
        description=f"{slug} description",
        color="#333333",
        is_visible=True,
        is_open_for_posting=True,
    )
    defaults.update(kwargs)
    return Room.objects.create(slug=slug, **defaults)


def _login(client, user):
    session = Session.create_for_user(user)
    client.cookies["token"] = session.token


class TestListRooms(TestCase):
    def setUp(self):
        self.user = _create_user("rooms_viewer")
        self.client = Client()
        _login(self.client, self.user)

    def test_renders_toggle_state_with_bulk_queries(self):
        subscribed_room = _create_room("subscribed-room")
        muted_room = _create_room("muted-room")
        _create_room("plain-room")

        RoomSubscription.objects.create(user=self.user, room=subscribed_room)
        RoomMuted.objects.create(user=self.user, room=muted_room)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get("/rooms/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "подписаться на комнату", count=3)
        self.assertContains(response, "посты видны на главной", count=3)
        self.assertContains(response, '/subscribe/"', count=3)
        self.assertContains(response, '/mute/"', count=3)
        self.assertContains(response, "is-active-by-default", count=3)

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
