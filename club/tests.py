import json
from datetime import datetime, timedelta

from django.test import TestCase

from debug.helpers import HelperClient
from posts.models.post import Post
from rooms.models import Room
from users.models.user import User


class JsonApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            email="jsontest@test.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="testuser",
            full_name="Test User",
        )
        cls.post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="test-post",
            title="Test Post Title",
            author=cls.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
            is_public=True,
        )

    def setUp(self):
        self.client = HelperClient(user=self.user)
        self.client.authorise()

    def get_json(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        return json.loads(response.content)


class FeedJsonTest(JsonApiTestCase):
    def test_format_param(self):
        data = self.get_json("/?format=json")
        self.assertIn("posts", data)
        self.assertIn("items", data["posts"])
        self.assertIn("page", data["posts"])
        self.assertIn("has_next", data["posts"])

    def test_json_suffix(self):
        data = self.get_json("/.json")
        self.assertIn("posts", data)

    def test_accept_header(self):
        response = self.client.get("/", HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("posts", data)

    def test_html_still_works(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])


class PostJsonTest(JsonApiTestCase):
    def test_post_detail(self):
        data = self.get_json(f"/post/{self.post.slug}/?format=json")
        self.assertIn("post", data)
        self.assertIn("comments", data)

    def test_post_json_suffix(self):
        data = self.get_json(f"/post/{self.post.slug}/.json")
        self.assertIn("post", data)

    def test_post_no_sensitive_keys(self): # специальный тест для Андрея
        data = self.get_json(f"/post/{self.post.slug}/?format=json")
        for key in ("muted_user_ids", "user_notes", "moderator_notes", "subscription"):
            self.assertNotIn(key, data)


class ProfileJsonTest(JsonApiTestCase):
    def test_profile(self):
        data = self.get_json(f"/user/{self.user.slug}/?format=json")
        self.assertIn("user", data)

    def test_no_sensitive_keys(self):
        data = self.get_json(f"/user/{self.user.slug}/?format=json")
        for key in ("muted_user_ids", "user_notes", "moderator_notes", "note", "muted", "subscription"):
            self.assertNotIn(key, data)

    def test_no_email_in_profile(self):
        data = self.get_json(f"/user/{self.user.slug}/?format=json")
        user_data = data["user"]
        self.assertNotIn("email", user_data)
        self.assertNotIn("telegram", user_data)


class BookmarksJsonTest(JsonApiTestCase):
    def test_bookmarks(self):
        data = self.get_json("/bookmarks/?format=json")
        self.assertIn("posts", data)
        self.assertIn("items", data["posts"])


class RoomsJsonTest(JsonApiTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Room.objects.create(slug="test-room", title="Test Room", color="#000", is_visible=True)

    def test_rooms(self):
        data = self.get_json("/rooms/?format=json")
        self.assertIn("rooms", data)
        self.assertEqual(len(data["rooms"]), 1)


class ExistingEndpointsTest(JsonApiTestCase):
    def test_feed_json(self):
        response = self.client.get("/feed.json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("version", data)
        self.assertIn("items", data)

    def test_user_json(self):
        response = self.client.get(f"/user/{self.user.slug}.json")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["slug"], self.user.slug)


class SerializerTest(TestCase):
    def test_primitives(self):
        from club.serializers import serialize
        self.assertIsNone(serialize(None))
        self.assertEqual(serialize(42), 42)
        self.assertEqual(serialize("hello"), "hello")
        self.assertIs(serialize(True), True)

    def test_datetime(self):
        from club.serializers import serialize
        result = serialize(datetime(2024, 1, 15, 12, 30))
        self.assertEqual(result, "2024-01-15T12:30:00")

    def test_skip_keys(self):
        from club.serializers import serialize
        result = serialize({"csrf_token": "x", "request": "y", "title": "ok"})
        self.assertEqual(result, {"title": "ok"})

    def test_sensitive_keys(self):
        from club.serializers import serialize
        result = serialize({"muted_user_ids": [1], "user_notes": {}, "name": "ok"})
        self.assertEqual(result, {"name": "ok"})

    def test_underscore_keys(self):
        from club.serializers import serialize
        result = serialize({"_private": "x", "public": "ok"})
        self.assertEqual(result, {"public": "ok"})
