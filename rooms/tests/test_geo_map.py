import json
from datetime import datetime, timedelta

from django.test import TestCase

from authn.models.session import Session
from map.templatetags.map import rooms_map_geo_json
from misc.models import NetworkGroup
from rooms.models import Room
from users.models.user import User


def _create_group(code="geo_europe"):
    return NetworkGroup.objects.create(code=code, title=code)


def _create_room(slug, group, **kwargs):
    defaults = dict(
        title=slug,
        color="#FFCC00",
        is_visible=True,
        network_group=group,
        latitude=52.52,
        longitude=13.405,
        chat_url="https://t.me/example",
        image="https://example.com/room.jpg",
        icon="🇩🇪",
        chat_member_count=10,
    )
    defaults.update(kwargs)
    return Room.objects.create(slug=slug, **defaults)


class TestRoomMapFeatures(TestCase):
    def setUp(self):
        self.group = _create_group()
        self.room = _create_room(
            "berlin",
            self.group,
            title="Берлин",
            subtitle="столица",
        )

    def test_marker_feature_uses_lng_lat_and_chat_redirect(self):
        feature = self.room.to_map_marker_feature()

        self.assertEqual(feature["geometry"]["coordinates"], [13.405, 52.52])
        self.assertEqual(feature["properties"]["id"], "berlin")
        self.assertEqual(feature["properties"]["title"], "Берлин")
        self.assertEqual(feature["properties"]["url"], "/room/berlin/chat/")
        self.assertEqual(feature["properties"]["member_count"], 10)
        self.assertEqual(feature["properties"]["image"], "https://example.com/room.jpg")
        self.assertNotIn("subtitle", feature["properties"])

    def test_marker_has_no_url_without_chat(self):
        self.room.chat_url = None
        self.room.url = None
        self.room.save()

        self.assertIsNone(self.room.to_map_marker_feature()["properties"]["url"])

    def test_skips_incomplete_map_data(self):
        self.room.latitude = None
        self.assertIsNone(self.room.to_map_marker_feature())


class TestRoomsMapGeoJson(TestCase):
    def test_serializes_markers_as_a_feature_collection(self):
        group = _create_group()
        berlin = _create_room(
            "berlin",
            group,
            title="Берлин",
            geojson={
                "type": "Polygon",
                "coordinates": [[[13.0, 52.3], [13.8, 52.3], [13.8, 52.7], [13.0, 52.7], [13.0, 52.3]]],
            },
        )
        london = _create_room("london", group, title="Лондон", geojson=None, latitude=51.5, longitude=-0.12)

        payload = json.loads(rooms_map_geo_json([berlin, london]))

        self.assertEqual(payload["type"], "FeatureCollection")
        self.assertEqual(payload["id"], "room-markers")
        self.assertEqual(len(payload["features"]), 2)
        self.assertNotIn("areas", payload)


class TestPeoplePageRendersRooms(TestCase):
    def setUp(self):
        user = User.objects.create(
            slug="tgeoroom_viewer",
            email="tgeoroom_viewer@test.com",
            full_name="Viewer",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
        )
        session = Session.create_for_user(user)
        self.client.cookies["token"] = session.token
        self.group = _create_group()

    def test_injects_geo_rooms_into_the_map_component(self):
        _create_room("berlin", self.group, title="Берлин")

        response = self.client.get("/people/")
        content = response.content.decode()

        self.assertEqual(list(response.context["geo_rooms"]), [Room.objects.get(slug="berlin")])
        self.assertIn("rooms=", content)
        self.assertIn("&quot;id&quot;: &quot;berlin&quot;", content)

    def test_skips_non_geo_hidden_and_unlocated_rooms(self):
        chats = _create_group("chats")
        _create_room("tech-chat", chats, title="Тех")
        _create_room("hidden", self.group, is_visible=False)
        _create_room("no-coords", self.group, latitude=None, longitude=None)

        response = self.client.get("/people/")

        self.assertEqual(list(response.context["geo_rooms"]), [])

    def test_keeps_visible_geo_rooms_closed_for_posting(self):
        ukraine = _create_room("ua", self.group, title="Украина", is_open_for_posting=False)

        response = self.client.get("/people/")

        self.assertEqual(list(response.context["geo_rooms"]), [ukraine])
        self.assertIn("&quot;id&quot;: &quot;ua&quot;", response.content.decode())

    def test_messages_only_filter_hides_geo_rooms(self):
        _create_room("berlin", self.group, title="Берлин")

        people_page = self.client.get("/people/")
        self.assertEqual(list(people_page.context["geo_rooms"]), [Room.objects.get(slug="berlin")])

        messages_only = self.client.get("/people/?filters=messages_only")
        self.assertEqual(list(messages_only.context["geo_rooms"]), [])
        content = messages_only.content.decode()
        self.assertIn("room-markers", content)
        self.assertIn("&quot;features&quot;: []", content)
