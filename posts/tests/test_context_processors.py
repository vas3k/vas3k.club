from django.test import TestCase, RequestFactory

from posts.context_processors.feed import rooms
from rooms.models import Room


class RoomsContextProcessorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        Room.objects.create(
            slug="test-room",
            title="Test Room",
            is_visible=True,
            is_open_for_posting=True,
        )

    def test_rooms_returns_rooms(self):
        request = self.factory.get("/")
        context = rooms(request)
        self.assertIn("rooms", context)
        self.assertNotIn("rooms_map", context)
        self.assertEqual(context["rooms"].count(), 1)

    def test_rooms_excludes_invisible_and_closed(self):
        Room.objects.create(
            slug="hidden-room",
            title="Hidden",
            is_visible=False,
            is_open_for_posting=True,
        )
        Room.objects.create(
            slug="closed-room",
            title="Closed",
            is_visible=True,
            is_open_for_posting=False,
        )
        request = self.factory.get("/")
        context = rooms(request)
        slugs = [r.slug for r in context["rooms"]]
        self.assertIn("test-room", slugs)
        self.assertNotIn("hidden-room", slugs)
        self.assertNotIn("closed-room", slugs)
