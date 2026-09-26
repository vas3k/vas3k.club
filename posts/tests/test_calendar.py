from datetime import datetime, timedelta

from django.test import TestCase, Client

from authn.models.session import Session
from posts.models.post import Post
from users.models.user import User


def _create_user(slug, **kwargs):
    defaults = dict(
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.utcnow() - timedelta(days=5),
        membership_expires_at=datetime.utcnow() + timedelta(days=365),
        moderation_status=User.MODERATION_STATUS_APPROVED,
        is_email_verified=True,
    )
    defaults.update(kwargs)
    return User.objects.create(slug=slug, **defaults)


def _login(client, user):
    session = Session.create_for_user(user)
    client.cookies["token"] = session.token


def _event_metadata(day, month, time="12:00:00"):
    return {
        "event": {
            "day": str(day),
            "month": str(month),
            "time": time,
            "timezone": "UTC",
            "location": "Club",
        }
    }


class TestEventCalendar(TestCase):
    def setUp(self):
        self.user = _create_user("tcal_user")
        self.client = Client()
        _login(self.client, self.user)
        self.now = datetime.utcnow()

    def _create_event_at(self, slug, event_at, **kwargs):
        defaults = dict(
            title=f"Post {slug}",
            text=f"Text of {slug}",
            type=Post.TYPE_EVENT,
            visibility=Post.VISIBILITY_EVERYWHERE,
            last_activity_at=event_at,
            metadata=_event_metadata(event_at.day, event_at.month, event_at.strftime("%H:%M:%S")),
            published_at=event_at,
            moderation_status=Post.MODERATION_NONE,
        )
        defaults.update(kwargs)
        return Post.objects.create(slug=slug, author=self.user, **defaults)

    def test_shows_upcoming_events_in_ascending_order(self):
        later = self._create_event_at("tcal_later", self.now + timedelta(days=40))
        sooner = self._create_event_at("tcal_sooner", self.now + timedelta(days=2))

        response = self.client.get("/calendar/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids[:2], [sooner.id, later.id])

    def test_hides_past_events(self):
        past = self._create_event_at("tcal_past", self.now - timedelta(days=10))
        future = self._create_event_at("tcal_future", self.now + timedelta(days=3))

        response = self.client.get("/calendar/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertNotIn(past.id, feed_ids)
        self.assertIn(future.id, feed_ids)

    def test_renders_timeline_without_feed_sorting(self):
        self._create_event_at("tcal_visible", self.now + timedelta(days=4))

        response = self.client.get("/calendar/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "feed-ordering")
        self.assertContains(response, "event-calendar")
        self.assertContains(response, "event-calendar-month")
        self.assertContains(response, "event-calendar-date-day")

    def test_event_feed_is_unchanged(self):
        past = self._create_event_at("tcal_feed_past", self.now - timedelta(days=10))

        response = self.client.get("/event/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertIn(past.id, feed_ids)
        self.assertContains(response, "feed-ordering")
        self.assertNotContains(response, "event-calendar")
