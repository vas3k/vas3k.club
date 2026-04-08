import json
from datetime import datetime, timedelta

from django.test import TestCase
from django.urls import reverse

from bookmarks.models import PostBookmark
from debug.helpers import HelperClient
from posts.models.post import Post
from rooms.models import Room
from users.models.friends import Friend
from users.models.user import User


class ApiTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="test@example.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="testuser",
            full_name="Test User",
        )
        self.client = HelperClient(self.user)
        self.client.authorise()

    def get_json(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        return json.loads(response.content)


class BookmarksApiTest(ApiTestBase):
    def test_bookmarks_empty(self):
        data = self.get_json(reverse("api_bookmarks"))
        self.assertEqual(data["posts"], [])
        self.assertEqual(data["page"], 1)

    def test_bookmarks_with_post(self):
        post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="bookmarked-post",
            title="Bookmarked Post",
            author=self.user,
            is_public=True,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        PostBookmark.objects.create(user=self.user, post=post)

        data = self.get_json(reverse("api_bookmarks"))
        self.assertEqual(len(data["posts"]), 1)
        self.assertIn("title", data["posts"][0])

    def test_bookmarks_requires_auth(self):
        anon = HelperClient()
        response = anon.get(reverse("api_bookmarks"))
        self.assertEqual(response.status_code, 400)


class RoomsApiTest(ApiTestBase):
    def test_rooms_empty(self):
        data = self.get_json(reverse("api_rooms"))
        self.assertEqual(data["rooms"], [])

    def test_rooms_list(self):
        Room.objects.create(
            slug="test-room",
            title="Test Room",
            color="#ff0000",
            is_visible=True,
        )
        Room.objects.create(
            slug="hidden-room",
            title="Hidden Room",
            color="#00ff00",
            is_visible=False,
        )

        data = self.get_json(reverse("api_rooms"))
        self.assertEqual(len(data["rooms"]), 1)
        self.assertEqual(data["rooms"][0]["slug"], "test-room")
        self.assertEqual(data["rooms"][0]["title"], "Test Room")

    def test_rooms_requires_auth(self):
        anon = HelperClient()
        response = anon.get(reverse("api_rooms"))
        self.assertEqual(response.status_code, 400)


class FriendsApiTest(ApiTestBase):
    def test_friends_empty(self):
        data = self.get_json(reverse("api_friends"))
        self.assertEqual(data["friends"], [])
        self.assertEqual(data["page"], 1)

    def test_friends_list(self):
        friend_user = User.objects.create(
            email="friend@example.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="frienduser",
            full_name="Friend User",
        )
        Friend.add_friend(user_from=self.user, user_to=friend_user)

        data = self.get_json(reverse("api_friends"))
        self.assertEqual(len(data["friends"]), 1)
        self.assertEqual(data["friends"][0]["user"]["slug"], "frienduser")
        self.assertEqual(data["friends"][0]["user"]["full_name"], "Friend User")

    def test_friends_no_private_data(self):
        friend_user = User.objects.create(
            email="secret@example.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug="secretuser",
        )
        Friend.add_friend(user_from=self.user, user_to=friend_user)

        data = self.get_json(reverse("api_friends"))
        user_data = data["friends"][0]["user"]
        self.assertNotIn("email", user_data)
        self.assertNotIn("telegram", user_data)

    def test_friends_requires_auth(self):
        anon = HelperClient()
        response = anon.get(reverse("api_friends"))
        self.assertEqual(response.status_code, 400)


class ExistingEndpointsTest(ApiTestBase):
    def test_feed_json(self):
        data = self.get_json(reverse("json_feed"))
        self.assertIn("items", data)

    def test_profile_json(self):
        data = self.get_json(
            reverse("api_profile", args=[self.user.slug])
        )
        self.assertIn("user", data)
        self.assertNotIn("email", data["user"])
