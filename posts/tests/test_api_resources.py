from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from bookmarks.models import PostBookmark
from debug.utils_for_tests import create_approved_user, login
from posts.models.post import Post
from posts.models.subscriptions import PostSubscription
from posts.models.votes import PostVote


class TestPostApiResources(TestCase):
    def setUp(self):
        self.author = create_approved_user("resource_author")
        self.voter = create_approved_user("resource_voter")
        self.post = Post.objects.create(
            slug="resource-post", type=Post.TYPE_POST, author=self.author,
            title="Resource post", visibility=Post.VISIBILITY_EVERYWHERE,
        )
        login(self.client, self.voter)
        self.vote_url = reverse("toggle_post_vote", args=[self.post.slug])

    def test_vote_methods_preserve_counters_under_repeated_requests(self):
        self.assertEqual(self.vote_url, f"/post/{self.post.slug}/votes.json")
        response = self.client.get(self.vote_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_voted"])
        self.assertFalse(PostVote.objects.exists())

        for method, expected_count in [(self.client.post, 1), (self.client.delete, 0)]:
            for attempt in range(2):
                with self.subTest(method=method, attempt=attempt):
                    response = method(self.vote_url)
                    self.post.refresh_from_db()
                    self.author.refresh_from_db()

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()["is_voted"], bool(expected_count))
                    self.assertEqual(response.json()["post"]["upvotes"], expected_count)
                    self.assertEqual(self.post.upvotes, expected_count)
                    self.assertEqual(self.author.upvotes, expected_count)
                    self.assertEqual(PostVote.objects.count(), expected_count)

    def test_expired_vote_cannot_be_retracted(self):
        self.client.post(self.vote_url)
        PostVote.objects.update(created_at=datetime.utcnow() - settings.RETRACT_VOTE_TIMEDELTA - timedelta(seconds=1))

        response = self.client.delete(self.vote_url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["is_voted"])
        self.assertEqual(response.json()["post"]["upvotes"], 1)
        self.post.refresh_from_db()
        self.author.refresh_from_db()
        self.assertEqual(self.post.upvotes, 1)
        self.assertEqual(self.author.upvotes, 1)
        self.assertEqual(PostVote.objects.count(), 1)

    def test_author_cannot_vote_for_own_post(self):
        login(self.client, self.author)

        response = self.client.post(self.vote_url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_voted"])
        self.assertFalse(PostVote.objects.exists())
        self.post.refresh_from_db()
        self.assertEqual(self.post.upvotes, 0)

    def test_bookmark_methods_are_idempotent_and_get_is_read_only(self):
        url = reverse("toggle_post_bookmark", args=[self.post.slug])
        self.assertEqual(url, f"/post/{self.post.slug}/bookmarks.json")

        response = self.client.get(url)

        self.assertFalse(response.json()["is_bookmarked"])
        self.assertFalse(PostBookmark.objects.exists())

        for method, expected_count in [(self.client.post, 1), (self.client.delete, 0)]:
            for attempt in range(2):
                response = method(url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["is_bookmarked"], bool(expected_count))
                self.assertEqual(PostBookmark.objects.filter(user=self.voter, post=self.post).count(), expected_count)

    def test_post_subscription_preserves_existing_comment_preference(self):
        url = reverse("toggle_post_subscription", args=[self.post.slug])
        self.assertEqual(url, f"/post/{self.post.slug}/subscriptions.json")
        PostSubscription.subscribe(self.voter, self.post, type=PostSubscription.TYPE_ALL_COMMENTS)

        self.client.get(url)
        self.client.post(url)
        self.client.post(url)

        subscription = PostSubscription.objects.get(user=self.voter, post=self.post)
        self.assertEqual(subscription.type, PostSubscription.TYPE_ALL_COMMENTS)

        self.client.delete(url)
        response = self.client.delete(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["is_subscribed"])
        self.assertFalse(PostSubscription.objects.exists())

    def test_participation_preserves_other_participants_and_repeated_delete_is_safe(self):
        url = reverse("toggle_post_event_participation", args=[self.post.slug])
        self.assertEqual(url, f"/post/{self.post.slug}/participants.json")
        self.post.metadata = {"event": {"participants": [str(self.author.id)]}}
        self.post.save()

        response = self.client.get(url)

        self.assertFalse(response.json()["is_participating"])
        self.assertFalse(PostSubscription.objects.exists())

        self.client.post(url)
        response = self.client.post(url)
        self.post.refresh_from_db()

        self.assertTrue(response.json()["is_participating"])
        self.assertCountEqual(self.post.metadata["event"]["participants"], [str(self.author.id), str(self.voter.id)])
        self.assertEqual(PostSubscription.objects.count(), 1)

        self.client.delete(url)
        PostSubscription.subscribe(self.voter, self.post)
        response = self.client.delete(url)
        self.post.refresh_from_db()

        self.assertFalse(response.json()["is_participating"])
        self.assertEqual(self.post.metadata["event"]["participants"], [str(self.author.id)])
        self.assertTrue(PostSubscription.objects.filter(user=self.voter, post=self.post).exists())

    def test_unsupported_vote_method_does_not_write(self):
        response = self.client.put(self.vote_url)

        self.assertEqual(response.status_code, 405)
        self.assertFalse(PostVote.objects.exists())
