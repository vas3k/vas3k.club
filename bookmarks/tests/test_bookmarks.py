from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from debug.utils_for_tests import create_approved_user, login
from posts.models.post import Post
from bookmarks.models import PostBookmark


class TestBookmarksModel(TestCase):
    def setUp(self):
        self.user = create_approved_user("bookmark_user")
        self.client = Client()
        login(self.client, self.user)

        post = Post.objects.create(
            slug="bookmark-post",
            type=Post.TYPE_POST,
            title="Bookmark Post",
            text="Text",
            author=self.user,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )
        self.url = f"/post/{post.slug}/bookmark/"

    def test_toggle_post_bookmark_creates_and_deletes_relation(self):
        create_response = self.client.post(self.url)
        delete_response = self.client.post(self.url)

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["status"], "created")
        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json()["status"], "deleted")
        self.assertEqual(PostBookmark.objects.count(), 0)

    def test_toggle_post_bookmark_rejects_get_method(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class TestBookmarksView(TestCase):
    def setUp(self):
        self.user = create_approved_user("bookmarks_view_user")
        self.other_user = create_approved_user("bookmarks_view_other")
        self.client = Client()
        login(self.client, self.user)

    def _create_post(self, slug, author):
        return Post.objects.create(
            slug=slug,
            type=Post.TYPE_POST,
            title=slug,
            text=f"{slug} text",
            author=author,
            visibility=Post.VISIBILITY_EVERYWHERE,
        )

    def test_bookmarks_view_returns_only_user_non_deleted_posts_in_order(self):
        first = self._create_post("bookmark-first", self.user)
        second = self._create_post("bookmark-second", self.user)
        deleted = self._create_post("bookmark-deleted", self.user)
        foreign = self._create_post("bookmark-foreign", self.other_user)

        first_bookmark = PostBookmark.objects.create(user=self.user, post=first)
        second_bookmark = PostBookmark.objects.create(user=self.user, post=second)
        PostBookmark.objects.create(user=self.user, post=deleted)
        PostBookmark.objects.create(user=self.other_user, post=foreign)

        PostBookmark.objects.filter(id=first_bookmark.id).update(created_at=timezone.now() - timedelta(hours=2))
        PostBookmark.objects.filter(id=second_bookmark.id).update(created_at=timezone.now() - timedelta(hours=1))
        deleted.deleted_at = timezone.now()
        deleted.save(update_fields=["deleted_at"])

        response = self.client.get("/bookmarks/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([post.slug for post in response.context["posts"].object_list], ["bookmark-second", "bookmark-first"])
