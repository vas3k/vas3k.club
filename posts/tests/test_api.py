from datetime import datetime

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from debug.utils_for_tests import create_approved_user, login
from posts.models.post import Post

from posts.tests.test_views import ModelCreator


class TestApi(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.user = self.creator.create_user()
        self.time = datetime.now()

    def test_date_rfc3339(self):
        post = self.creator.create_post(
            is_public=True,
        )
        post.published_at = self.time
        post.updated_at = self.time
        converted_post = post.to_dict()
        self.assertIsNotNone(
            datetime.strptime(
                converted_post["date_published"], "%Y-%m-%dT%H:%M:%S.%f%z"
            ).tzinfo,
        )
        self.assertIsNotNone(
            datetime.strptime(
                converted_post["date_modified"], "%Y-%m-%dT%H:%M:%S.%f%z"
            ).tzinfo,
        )

    def test_content_text_is_not_none(self):
        post = self.creator.create_post(
            is_public=False,
        )
        converted_post = post.to_dict()
        self.assertIsNotNone(converted_post["content_text"])


class TestPostApiPrivacy(TestCase):
    def setUp(self):
        self.author = create_approved_user("post_api_author")
        self.viewer = create_approved_user("post_api_viewer")
        self.post = Post.objects.create(
            slug="private-api-draft", type=Post.TYPE_POST, author=self.author,
            title="Private draft", text="Secret draft body", visibility=Post.VISIBILITY_DRAFT,
        )

    def test_other_member_cannot_read_draft_or_its_comments(self):
        login(self.client, self.viewer)

        for name in ["api_show_post", "api_list_post_comments"]:
            with self.subTest(endpoint=name):
                response = self.client.get(reverse(name, args=[self.post.type, self.post.slug]))

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["error"]["code"], "Http404")
                self.assertNotIn(self.post.text, response.content.decode())

    def test_author_can_read_own_draft_without_query_flags(self):
        login(self.client, self.author)

        response = self.client.get(reverse("api_show_post", args=[self.post.type, self.post.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["post"]["content_text"], self.post.text)


class TestPublishedJsonFeeds(TestCase):
    def setUp(self):
        self.user = create_approved_user("feed_reader")
        self.public_post = Post.objects.create(
            slug="public-feed-post", type=Post.TYPE_POST, author=self.user,
            title="Public feed post", text="Public feed content", is_public=True,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        self.private_post = Post.objects.create(
            slug="private-feed-post", type=Post.TYPE_POST, author=self.user,
            title="Private feed post", text="Members-only feed content", is_public=False,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

    def test_published_feed_url_preserves_format_and_anonymous_privacy(self):
        url = reverse("json_feed")
        response = self.client.get(url)

        self.assertEqual(url, "/feed.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/feed+json")
        payload = response.json()
        self.assertEqual(payload["version"], "https://jsonfeed.org/version/1.1")
        self.assertEqual(payload["feed_url"], settings.APP_HOST + "/feed.json")
        items = {item["_club"]["slug"]: item for item in payload["items"]}
        self.assertEqual(items[self.public_post.slug]["content_text"], self.public_post.text)
        self.assertIn(self.private_post.slug, items)
        self.assertNotIn(self.private_post.text, response.content.decode())

    def test_ordered_feed_keeps_published_url_and_type_filter(self):
        other = Post.objects.create(
            slug="intro-feed-post", type=Post.TYPE_INTRO, author=self.user,
            title="Intro feed post", text="Intro content", is_public=True,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        url = reverse("json_feed_ordering", kwargs={"post_type": "post", "ordering": "top"})

        response = self.client.get(url)

        self.assertEqual(url, "/post/top/feed.json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"], "application/feed+json")
        slugs = [item["_club"]["slug"] for item in response.json()["items"]]
        self.assertCountEqual(slugs, [self.public_post.slug, self.private_post.slug])
        self.assertNotIn(other.slug, slugs)
        self.assertNotIn(self.private_post.text, response.content.decode())

    def test_authenticated_feed_keeps_member_content_available(self):
        login(self.client, self.user)

        response = self.client.get(reverse("json_feed"))

        self.assertEqual(response.status_code, 200)
        items = {item["_club"]["slug"]: item for item in response.json()["items"]}
        self.assertEqual(items[self.private_post.slug]["content_text"], self.private_post.text)
