from datetime import datetime, timedelta

from django.test import TestCase

from posts.models.post import Post
from users.models.user import User


class PostModelTestBase(TestCase):
    def setUp(self):
        self._user_counter = 0
        self.user = self._create_user()

    def _create_user(self, **kwargs):
        self._user_counter += 1
        defaults = dict(
            email=f"postmodel_test_{self._user_counter}@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
            moderation_status=User.MODERATION_STATUS_APPROVED,
            slug=f"postmodel_user_{self._user_counter}",
        )
        defaults.update(kwargs)
        return User.objects.create(**defaults)


class TestCoauthorsWithDetails(PostModelTestBase):
    def test_empty_coauthors_returns_empty_list(self):
        """Post with no coauthors should return empty list without querying DB."""
        post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="coauthor_empty",
            title="No Coauthors",
            text="test",
            author=self.user,
            coauthors=[],
        )
        self.assertEqual(post.coauthors_with_details, [])

    def test_returns_user_objects_for_coauthors(self):
        """Post with coauthors should return corresponding User objects."""
        coauthor_1 = self._create_user()
        coauthor_2 = self._create_user()
        post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="coauthor_filled",
            title="With Coauthors",
            text="test",
            author=self.user,
            coauthors=[coauthor_1.slug, coauthor_2.slug],
        )
        result = post.coauthors_with_details
        result_slugs = {u.slug for u in result}
        self.assertEqual(result_slugs, {coauthor_1.slug, coauthor_2.slug})

    def test_nonexistent_coauthor_slug_ignored(self):
        """Coauthor slug that doesn't match any user should be silently skipped."""
        coauthor = self._create_user()
        post = Post.objects.create(
            type=Post.TYPE_POST,
            slug="coauthor_partial",
            title="Partial Coauthors",
            text="test",
            author=self.user,
            coauthors=[coauthor.slug, "nonexistent_slug"],
        )
        result = post.coauthors_with_details
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].slug, coauthor.slug)


class TestEventParticipants(PostModelTestBase):
    def _create_event_post(self, participant_ids):
        return Post.objects.create(
            type=Post.TYPE_EVENT,
            slug=f"event_{self._user_counter}",
            title="Test Event",
            text="test",
            author=self.user,
            metadata={"event": {"participants": participant_ids, "time": "12:00:00"}},
        )

    def test_empty_participants_returns_empty_list(self):
        post = self._create_event_post([])
        self.assertEqual(post.event_participants, [])

    def test_no_event_metadata_returns_empty_list(self):
        post = Post.objects.create(
            type=Post.TYPE_EVENT,
            slug="event_no_meta",
            title="No Meta Event",
            text="test",
            author=self.user,
            metadata={},
        )
        self.assertEqual(post.event_participants, [])

    def test_returns_users_in_participant_order(self):
        """Participants should be returned in the same order as stored in metadata."""
        user_a = self._create_user()
        user_b = self._create_user()
        post = self._create_event_post([str(user_b.id), str(user_a.id)])
        result = post.event_participants
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].id, user_b.id)
        self.assertEqual(result[1].id, user_a.id)

    def test_nonexistent_participant_id_ignored(self):
        user_a = self._create_user()
        post = self._create_event_post([str(user_a.id), "00000000-0000-0000-0000-000000000000"])
        result = post.event_participants
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, user_a.id)
