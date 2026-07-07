from datetime import datetime, timedelta

from django.test import TestCase, Client

from authn.models.session import Session
from posts.models.post import Post
from rooms.models import Room, RoomMuted, RoomSubscription
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


def _create_post(slug, author, **kwargs):
    defaults = dict(
        title=f"Post {slug}",
        text=f"Text of {slug}",
        type=Post.TYPE_POST,
        visibility=Post.VISIBILITY_EVERYWHERE,
        published_at=datetime.utcnow() - timedelta(hours=1),
        last_activity_at=datetime.utcnow() - timedelta(hours=1),
        moderation_status=Post.MODERATION_NONE,
    )
    defaults.update(kwargs)
    return Post.objects.create(slug=slug, author=author, **defaults)


def _create_room(slug, **kwargs):
    defaults = dict(
        title=slug,
        description=f"{slug} description",
        color="#333333",
        is_visible=True,
        is_open_for_posting=True,
    )
    defaults.update(kwargs)
    return Room.objects.create(slug=slug, **defaults)


def _login(client, user):
    session = Session.create_for_user(user)
    client.cookies["token"] = session.token


class TestFeedPinnedPosts(TestCase):
    """Test that pinned posts appear separately and are excluded from the main feed."""

    def setUp(self):
        self.user = _create_user("tfeed_user")
        self.client = Client()
        _login(self.client, self.user)

    def test_pinned_post_appears_in_pinned_list(self):
        pinned = _create_post("tfeed_pinned", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])

        self.assertEqual(len(pinned_posts), 1)
        self.assertEqual(pinned_posts[0].id, pinned.id)

    def test_pinned_post_excluded_from_main_feed(self):
        pinned = _create_post("tfeed_pinned", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))
        regular = _create_post("tfeed_regular", self.user)

        response = self.client.get("/")
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertNotIn(pinned.id, feed_ids)
        self.assertIn(regular.id, feed_ids)

    def test_expired_pinned_post_in_main_feed(self):
        expired = _create_post("tfeed_expired", self.user,
                               is_pinned_until=datetime.utcnow() - timedelta(hours=1))

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(len(pinned_posts), 0)
        self.assertIn(expired.id, feed_ids)

    def test_null_pinned_until_in_main_feed(self):
        regular = _create_post("tfeed_null_pin", self.user, is_pinned_until=None)

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(len(pinned_posts), 0)
        self.assertIn(regular.id, feed_ids)

    def test_multiple_regular_posts_not_lost(self):
        posts = []
        for i in range(5):
            posts.append(_create_post(f"tfeed_reg_{i}", self.user))

        response = self.client.get("/")
        feed_ids = [p.id for p in response.context["posts"]]

        for p in posts:
            self.assertIn(p.id, feed_ids)

    def test_pinned_and_regular_together(self):
        pinned = _create_post("tfeed_pinned", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))
        regulars = [_create_post(f"tfeed_reg_{i}", self.user) for i in range(3)]

        response = self.client.get("/")
        pinned_posts = list(response.context["pinned_posts"])
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(len(pinned_posts), 1)
        self.assertEqual(pinned_posts[0].id, pinned.id)
        self.assertNotIn(pinned.id, feed_ids)
        for r in regulars:
            self.assertIn(r.id, feed_ids)

    def test_draft_posts_excluded(self):
        draft = _create_post("tfeed_draft", self.user,
                             visibility=Post.VISIBILITY_DRAFT)

        response = self.client.get("/")
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertNotIn(draft.id, feed_ids)

    def test_non_activity_ordering_skips_pinning(self):
        pinned = _create_post("tfeed_pinned_new", self.user,
                              is_pinned_until=datetime.utcnow() + timedelta(days=1))

        response = self.client.get("/all/new/")
        pinned_posts = response.context["pinned_posts"]
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(pinned_posts, [])
        self.assertIn(pinned.id, feed_ids)


class TestFeedSortingAndVisibility(TestCase):
    def setUp(self):
        self.user = _create_user("tfeed_sort_user")
        self.client = Client()
        _login(self.client, self.user)

    def test_new_ordering_sorts_by_published_at_desc(self):
        older = _create_post(
            "tfeed_new_old",
            self.user,
            published_at=datetime.utcnow() - timedelta(days=2),
        )
        newer = _create_post(
            "tfeed_new_new",
            self.user,
            published_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = self.client.get("/all/new/")
        posts = list(response.context["posts"])
        feed_ids = [post.id for post in posts]

        self.assertLess(feed_ids.index(newer.id), feed_ids.index(older.id))

    def test_hot_ordering_sorts_by_hotness_desc(self):
        cold = _create_post("tfeed_hot_cold", self.user, hotness=1)
        hot = _create_post("tfeed_hot_hot", self.user, hotness=100)

        response = self.client.get("/all/hot/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertLess(feed_ids.index(hot.id), feed_ids.index(cold.id))

    def test_activity_ordering_sorts_by_last_activity_desc(self):
        stale = _create_post(
            "tfeed_activity_stale",
            self.user,
            last_activity_at=datetime.utcnow() - timedelta(days=1),
        )
        active = _create_post(
            "tfeed_activity_active",
            self.user,
            last_activity_at=datetime.utcnow() - timedelta(minutes=5),
        )

        response = self.client.get("/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertLess(feed_ids.index(active.id), feed_ids.index(stale.id))

    def test_muted_room_hidden_on_main_feed_but_visible_in_room_feed(self):
        room = _create_room("tfeed-muted-room")
        post = _create_post("tfeed_muted_room_post", self.user, room=room)
        RoomMuted.objects.create(user=self.user, room=room)

        main_response = self.client.get("/")
        room_response = self.client.get(f"/room/{room.slug}/")

        self.assertNotIn(post.id, [p.id for p in main_response.context["posts"]])
        self.assertIn(post.id, [p.id for p in room_response.context["posts"]])

    def test_room_only_posts_hidden_for_unsubscribed_user(self):
        room = _create_room("tfeed-room-only")
        room_only = _create_post("tfeed_room_only", self.user, room=room, is_room_only=True)
        regular = _create_post("tfeed_regular_visible", self.user)

        response = self.client.get("/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertNotIn(room_only.id, feed_ids)
        self.assertIn(regular.id, feed_ids)

    def test_room_only_posts_visible_for_subscribed_user(self):
        room = _create_room("tfeed-room-only-sub")
        room_only = _create_post("tfeed_room_only_sub", self.user, room=room, is_room_only=True)
        RoomSubscription.objects.create(user=self.user, room=room)

        response = self.client.get("/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertIn(room_only.id, feed_ids)

    def test_invalid_top_month_ordering_param_returns_404(self):
        response = self.client.get("/all/top_month:2024-99/")
        self.assertEqual(response.status_code, 404)

    def test_invalid_top_year_ordering_param_returns_404(self):
        response = self.client.get("/all/top_year:twenty/")
        self.assertEqual(response.status_code, 404)

    def test_moderator_sees_pending_posts_in_activity_feed(self):
        moderator = _create_user("tfeed_mod", roles=[User.ROLE_MODERATOR])
        other = _create_user("tfeed_pending_author")
        own_pending = _create_post("tfeed_own_pending", moderator, moderation_status=Post.MODERATION_PENDING)
        other_pending = _create_post("tfeed_other_pending", other, moderation_status=Post.MODERATION_PENDING)

        _login(self.client, moderator)
        response = self.client.get("/")
        pending_ids = [post.id for post in response.context["waiting_for_moderation_posts"]]

        self.assertIn(other_pending.id, pending_ids)
        self.assertNotIn(own_pending.id, pending_ids)
