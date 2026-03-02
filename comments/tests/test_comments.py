from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from comments.models import Comment
from comments.views import create_comment
from debug.helpers import HelperClient
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from posts.tests.test_views import ModelCreator


class PostSubscriptionCreator(ModelCreator):
    def create_subscription(self, user, post):
        return PostSubscription.objects.create(user=user, post=post, type="all")


class TestComments(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        subscr_creator = PostSubscriptionCreator()
        self.post = self.creator.create_post(
            is_public=True,
        )
        self.author_user = self.post.author
        self.user_subscription = subscr_creator.create_subscription(
            self.author_user, self.post
        )

        rf = RequestFactory()
        self.comment_request = rf.post(
            (f"post/{self.post.id}/comment/create/", self.post.id),
            data={"text": "lorem ipsum", "subscribe_to_post": True},
        )

    def test_is_author_subscription_not_downgraded(self):
        self.comment_request.me = self.author_user

        self.assertEqual(
            self.user_subscription.type, PostSubscription.TYPE_ALL_COMMENTS
        )
        create_comment(self.comment_request, self.post.slug)
        self.user_subscription = PostSubscription.objects.get(
            user=self.author_user, post=self.post
        )
        self.assertEqual(
            self.user_subscription.type, PostSubscription.TYPE_ALL_COMMENTS
        )

    def test_is_usual_subscription_working(self):
        not_author_user = self.creator.create_user()
        self.comment_request.me = not_author_user
        self.assertRaises(
            PostSubscription.DoesNotExist,
            PostSubscription.objects.get,
            user=not_author_user,
            post=self.post,
        )
        create_comment(self.comment_request, self.post.slug)
        not_author_subscription = PostSubscription.objects.get(
            user=not_author_user, post=self.post
        )
        self.assertEqual(
            not_author_subscription.type, PostSubscription.TYPE_TOP_LEVEL_ONLY
        )


class TestCommentHttpMethods(TestCase):
    """
    Tests for issue #746: modifying actions should reject GET requests.
    https://github.com/vas3k/vas3k.club/issues/746
    """

    def setUp(self):
        self.creator = ModelCreator()
        self.post = self.creator.create_post(is_public=True)
        self.comment_author = self.post.author
        self.comment = Comment.objects.create(
            author=self.comment_author,
            post=self.post,
            text="Test comment"
        )

    def test_delete_comment_rejects_get_request(self):
        """GET request to delete_comment should return 405 Method Not Allowed"""
        client = HelperClient(self.comment_author)
        client.authorise()

        url = reverse("delete_comment", args=[self.comment.id])
        response = client.get(url)

        self.assertEqual(response.status_code, 405)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)

    def test_delete_comment_accepts_post_request(self):
        """POST request to delete_comment should work"""
        client = HelperClient(self.comment_author)
        client.authorise()

        url = reverse("delete_comment", args=[self.comment.id])
        response = client.post(url)

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)

    def test_pin_comment_rejects_get_request(self):
        """GET request to pin_comment should return 405 Method Not Allowed"""
        client = HelperClient(self.comment_author)
        client.authorise()

        url = reverse("pin_comment", args=[self.comment.id])
        response = client.get(url)

        self.assertEqual(response.status_code, 405)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_pinned)

    def test_pin_comment_accepts_post_request(self):
        """POST request to pin_comment should work"""
        client = HelperClient(self.comment_author)
        client.authorise()

        url = reverse("pin_comment", args=[self.comment.id])
        response = client.post(url)

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_pinned)


class TestDeleteComment(TestCase):
    def setUp(self):
        self.creator = ModelCreator()
        self.post = self.creator.create_post(is_public=True)
        self.comment_author = self.post.author
        self.other_user = self.creator.create_user()
        self.moderator = self.creator.create_user()
        self.moderator.roles = ["moderator"]
        self.moderator.save()

        self.comment = Comment.objects.create(
            author=self.comment_author,
            post=self.post,
            text="Test comment",
        )

    def _delete_url(self):
        return reverse("delete_comment", args=[self.comment.id])

    def test_author_can_delete_own_comment(self):
        client = HelperClient(self.comment_author)
        client.authorise()

        response = client.post(self._delete_url())

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)
        self.assertEqual(self.comment.deleted_by, self.comment_author.id)

    def test_post_author_can_delete_comment(self):
        other_comment = Comment.objects.create(
            author=self.other_user,
            post=self.post,
            text="Someone else's comment",
        )
        client = HelperClient(self.comment_author)  # post author
        client.authorise()

        url = reverse("delete_comment", args=[other_comment.id])
        response = client.post(url)

        self.assertEqual(response.status_code, 302)
        other_comment.refresh_from_db()
        self.assertTrue(other_comment.is_deleted)
        self.assertEqual(other_comment.deleted_by, self.comment_author.id)

    def test_moderator_can_delete_any_comment(self):
        client = HelperClient(self.moderator)
        client.authorise()

        response = client.post(self._delete_url())

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)

    def test_random_user_cannot_delete_comment(self):
        client = HelperClient(self.other_user)
        client.authorise()

        response = client.post(self._delete_url())

        self.assertIn(response.status_code, [403, 302])
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)

    def test_undelete_by_same_user(self):
        self.comment.delete(deleted_by=self.comment_author)
        client = HelperClient(self.comment_author)
        client.authorise()

        response = client.post(self._delete_url())

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)
        self.assertIsNone(self.comment.deleted_by)

    def test_undelete_by_moderator(self):
        self.comment.delete(deleted_by=self.comment_author)
        client = HelperClient(self.moderator)
        client.authorise()

        response = client.post(self._delete_url())

        self.assertEqual(response.status_code, 302)
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)

    def test_undelete_by_wrong_user_denied(self):
        self.comment.delete(deleted_by=self.comment_author)
        client = HelperClient(self.other_user)
        client.authorise()

        response = client.post(self._delete_url())

        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)

    def test_delete_toggle_by_same_user(self):
        """Same user can delete and then undelete their comment"""
        client = HelperClient(self.comment_author)
        client.authorise()

        client.post(self._delete_url())
        self.comment.refresh_from_db()
        self.assertTrue(self.comment.is_deleted)

        client.post(self._delete_url())
        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)

    def test_anonymous_cannot_delete(self):
        client = HelperClient()
        url = self._delete_url()
        response = client.post(url)

        self.comment.refresh_from_db()
        self.assertFalse(self.comment.is_deleted)


class TestCommentThreadDeletion(TestCase):
    """Tests for delete_comment_thread endpoint"""

    def setUp(self):
        self.creator = ModelCreator()
        self.moderator = self.creator.create_user()
        self.moderator.roles = ["moderator"]
        self.moderator.save()

        self.post = self.creator.create_post()
        self.comment = Comment.objects.create(
            author=self.post.author,
            post=self.post,
            text="Parent comment"
        )

    def test_delete_thread_rejects_get_request(self):
        """GET request to delete_comment_thread should return 405"""
        client = HelperClient(self.moderator)
        client.authorise()

        url = reverse("delete_comment_thread", args=[self.comment.id])
        response = client.get(url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Comment.objects.filter(id=self.comment.id).exists())

    def test_delete_thread_accepts_post_request(self):
        """POST request to delete_comment_thread should work"""
        client = HelperClient(self.moderator)
        client.authorise()

        url = reverse("delete_comment_thread", args=[self.comment.id])
        response = client.post(url)

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=self.comment.id).exists())
