from datetime import datetime, timedelta

from django.test import TestCase, Client

from debug.utils_for_tests import create_approved_user, login
from posts.models.post import Post


class TestEventCalendar(TestCase):
    def setUp(self):
        self.user = create_approved_user("tcal_user")
        self.client = Client()
        login(self.client, self.user)
        self.now = datetime.utcnow()

    def create_event_at(self, slug, event_at, **kwargs):
        defaults = dict(
            title=f"Post {slug}",
            text=f"Text of {slug}",
            type=Post.TYPE_EVENT,
            visibility=Post.VISIBILITY_EVERYWHERE,
            last_activity_at=event_at,
            metadata={
                "event": {
                    "day": str(event_at.day),
                    "month": str(event_at.month),
                    "time": event_at.strftime("%H:%M:%S"),
                    "timezone": "UTC",
                    "location": "Club",
                }
            },
            published_at=event_at,
            moderation_status=Post.MODERATION_NONE,
        )
        defaults.update(kwargs)
        return Post.objects.create(slug=slug, author=self.user, **defaults)

    def test_shows_upcoming_events_in_ascending_order(self):
        later = self.create_event_at("tcal_later", self.now + timedelta(days=40))
        sooner = self.create_event_at("tcal_sooner", self.now + timedelta(days=2))

        response = self.client.get("/calendar/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids[:2], [sooner.id, later.id])

    def test_hides_past_events(self):
        past = self.create_event_at("tcal_past", self.now - timedelta(days=10))
        future = self.create_event_at("tcal_future", self.now + timedelta(days=3))

        response = self.client.get("/calendar/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertNotIn(past.id, feed_ids)
        self.assertIn(future.id, feed_ids)

    def test_event_feed_is_unchanged(self):
        past = self.create_event_at("tcal_feed_past", self.now - timedelta(days=10))

        response = self.client.get("/event/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertIn(past.id, feed_ids)
