from django.test import TestCase, RequestFactory

from posts.context_processors.feed import rooms, ordering, ORDERING_LAST_MONTHS
from posts.helpers import ORDERING_TOP, ORDERING_TOP_WEEK, ORDERING_TOP_MONTH, ORDERING_TOP_YEAR
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
        self.assertEqual([room.slug for room in context["rooms"]], ["test-room"])

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


class OrderingContextProcessorTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_ordering_returns_expected_options(self):
        request = self.factory.get("/")
        context = ordering(request)
        values = [option["value"] for option in context["feed_ordering_options"]]

        self.assertEqual(values, [ORDERING_TOP, ORDERING_TOP_YEAR, ORDERING_TOP_MONTH, ORDERING_TOP_WEEK])

    def test_ordering_returns_months_and_years_ranges(self):
        request = self.factory.get("/")
        context = ordering(request)

        months = context["feed_ordering_months"]
        years = context["feed_ordering_years"]

        self.assertEqual(months[0]["value"], ORDERING_TOP_MONTH)
        self.assertEqual(len(months), ORDERING_LAST_MONTHS + 1)
        self.assertTrue(months[1]["value"].startswith(f"{ORDERING_TOP_MONTH}:"))

        self.assertEqual(years[0]["value"], ORDERING_TOP_YEAR)
        self.assertTrue(any(v["value"].startswith(f"{ORDERING_TOP_YEAR}:") for v in years[1:]))
