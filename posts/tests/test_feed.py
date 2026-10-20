from datetime import datetime, timedelta

from django.test import TestCase, Client

from authn.models.session import Session
from posts.models.post import Post
from rooms.models import Room, RoomMuted, RoomSubscription
from users.models.mute import UserMuted
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
        pinned_posts = list(response.context["pinned_posts"])
        feed_ids = [p.id for p in response.context["posts"]]

        self.assertEqual(pinned_posts, [])
        self.assertIn(pinned.id, feed_ids)


class TestFeedSortingAndVisibility(TestCase):
    def setUp(self):
        self.user = _create_user("tfeed_sort_user")
        self.client = Client()
        _login(self.client, self.user)

    def test_rejected_posts_are_mixed_into_new_feed_by_date(self):
        self.user.roles = [User.ROLE_MODERATOR]
        self.user.save()
        rejected = _create_post(
            "new_feed_rejected",
            _create_user("new_feed_rejected_author"),
            moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT,
            published_at=None,
        )
        Post.objects.filter(id=rejected.id).update(
            updated_at=datetime.utcnow() - timedelta(days=2),
            last_activity_at=datetime.utcnow() - timedelta(days=2),
        )
        stale = _create_post(
            "new_feed_stale_rejected",
            _create_user("new_feed_stale_author"),
            moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT,
            published_at=None,
        )
        Post.objects.filter(id=stale.id).update(
            updated_at=datetime.utcnow() - timedelta(days=30),
            last_activity_at=datetime.utcnow() - timedelta(days=30),
        )
        newer = _create_post(
            "new_feed_newer",
            self.user,
            published_at=datetime.utcnow() - timedelta(hours=1),
        )

        response = self.client.get("/all/new/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertLess(feed_ids.index(newer.id), feed_ids.index(rejected.id))
        self.assertNotIn(stale.id, feed_ids)
        self.assertNotIn(rejected.id, [post.id for post in response.context["moderation_posts"]])

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

    def test_new_ordering_breaks_published_at_ties_by_created_at(self):
        published_at = datetime.utcnow() - timedelta(days=1)
        older = _create_post("tfeed_new_tie_old", self.user, published_at=published_at)
        newer = _create_post("tfeed_new_tie_new", self.user, published_at=published_at)

        response = self.client.get("/all/new/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertLess(feed_ids.index(newer.id), feed_ids.index(older.id))

    def test_top_ordering_sorts_by_upvotes_desc(self):
        low = _create_post("tfeed_top_low", self.user, upvotes=1)
        high = _create_post("tfeed_top_high", self.user, upvotes=50)

        response = self.client.get("/all/top/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids, [high.id, low.id])

    def test_top_week_keeps_posts_from_the_last_seven_days(self):
        recent = _create_post(
            "tfeed_week_recent", self.user, upvotes=1,
            published_at=datetime.utcnow() - timedelta(days=1),
        )
        older = _create_post(
            "tfeed_week_older", self.user, upvotes=100,
            published_at=datetime.utcnow() - timedelta(days=8),
        )

        response = self.client.get("/all/top_week/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids, [recent.id])
        self.assertNotIn(older.id, feed_ids)

    def test_top_month_uses_the_requested_month(self):
        inside = _create_post(
            "tfeed_month_inside", self.user, upvotes=2,
            published_at=datetime(2024, 3, 15, 12, 0, 0),
        )
        outside = _create_post(
            "tfeed_month_outside", self.user, upvotes=20,
            published_at=datetime(2024, 4, 1, 0, 0, 0),
        )

        response = self.client.get("/all/top_month:2024-03/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids, [inside.id])
        self.assertNotIn(outside.id, feed_ids)

    def test_top_month_default_window_is_thirty_one_days(self):
        recent = _create_post(
            "tfeed_month_recent", self.user, upvotes=1,
            published_at=datetime.utcnow() - timedelta(days=3),
        )
        older = _create_post(
            "tfeed_month_old", self.user, upvotes=10,
            published_at=datetime.utcnow() - timedelta(days=40),
        )

        response = self.client.get("/all/top_month/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids, [recent.id])
        self.assertNotIn(older.id, feed_ids)

    def test_top_year_uses_the_requested_year(self):
        inside = _create_post(
            "tfeed_year_inside", self.user, upvotes=3,
            published_at=datetime(2024, 6, 1, 12, 0, 0),
        )
        outside = _create_post(
            "tfeed_year_outside", self.user, upvotes=30,
            published_at=datetime(2025, 1, 1, 0, 0, 0),
        )

        response = self.client.get("/all/top_year:2024/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids, [inside.id])
        self.assertNotIn(outside.id, feed_ids)

    def test_top_year_default_window_is_one_year(self):
        recent = _create_post(
            "tfeed_year_recent", self.user, upvotes=1,
            published_at=datetime.utcnow() - timedelta(days=10),
        )
        older = _create_post(
            "tfeed_year_old", self.user, upvotes=10,
            published_at=datetime.utcnow() - timedelta(days=400),
        )

        response = self.client.get("/all/top_year/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids, [recent.id])
        self.assertNotIn(older.id, feed_ids)

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
        self.assertNotIn(post.id, [p.id for p in self.client.get("/all/hot/").context["posts"]])
        self.assertIn(post.id, [p.id for p in self.client.get("/all/top/").context["posts"]])

    def test_muted_author_is_hidden_in_main_and_room_feeds(self):
        author = _create_user("tfeed_muted_author")
        room = _create_room("tfeed-author-mute-room")
        post = _create_post("tfeed_muted_author_post", author, room=room)
        UserMuted.objects.create(user_from=self.user, user_to=author)

        for url in ["/", f"/room/{room.slug}/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotIn(post.id, [item.id for item in response.context["posts"]])

    def test_room_only_post_is_visible_inside_its_room_without_subscription(self):
        room = _create_room("tfeed-room-only-inside")
        room_only = _create_post("tfeed_room_only_inside", self.user, room=room, is_room_only=True)

        response = self.client.get(f"/room/{room.slug}/")

        self.assertIn(room_only.id, [post.id for post in response.context["posts"]])

    def test_label_feed_filters_by_label_and_keeps_room_only_posts(self):
        room = _create_room("tfeed-label-room")
        labeled = _create_post("tfeed_labeled", self.user, label_code="inside", room=room, is_room_only=True)
        other = _create_post("tfeed_other_label", self.user, label_code="ama")

        response = self.client.get("/label/inside/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertEqual(feed_ids, [labeled.id])
        self.assertNotIn(other.id, feed_ids)
        self.assertEqual(list(response.context["moderation_posts"]), [])

    def test_type_feed_filters_by_post_type(self):
        question = _create_post("tfeed_question", self.user, type=Post.TYPE_QUESTION)
        post = _create_post("tfeed_plain_post", self.user)

        question_ids = [item.id for item in self.client.get("/question/").context["posts"]]
        post_ids = [item.id for item in self.client.get("/post/").context["posts"]]

        self.assertEqual(question_ids, [question.id])
        self.assertEqual(post_ids, [post.id])

    def test_unknown_room_returns_404(self):
        response = self.client.get("/room/missing-feed-room/")
        self.assertEqual(response.status_code, 404)

    def test_link_only_posts_are_visible_only_to_their_author(self):
        author = _create_user("tfeed_link_author")
        foreign = _create_post(
            "tfeed_foreign_link", author, visibility=Post.VISIBILITY_LINK_ONLY,
        )
        own = _create_post("tfeed_own_link", self.user, visibility=Post.VISIBILITY_LINK_ONLY)

        response = self.client.get("/all/hot/")
        feed_ids = [post.id for post in response.context["posts"]]

        self.assertIn(own.id, feed_ids)
        self.assertNotIn(foreign.id, feed_ids)

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

    def test_staff_see_pending_posts_above_activity_feeds(self):
        other = _create_user("moderation_feed_author")
        room = _create_room("moderation-room")
        pending = _create_post(
            "moderation_pending", other, room=room, is_room_only=True,
            moderation_status=Post.MODERATION_PENDING, visibility=Post.VISIBILITY_LINK_ONLY,
        )
        Post.objects.filter(id=pending.id).update(created_at=datetime.utcnow() - timedelta(days=800))
        rejected = _create_post(
            "moderation_rejected", other, moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT, published_at=None,
        )
        own_pending = _create_post("moderation_own_pending", self.user, moderation_status=Post.MODERATION_PENDING)
        draft = _create_post("private_draft", other, visibility=Post.VISIBILITY_DRAFT)
        _create_post("withdrawn_pending", other, visibility=Post.VISIBILITY_DRAFT,
                     moderation_status=Post.MODERATION_PENDING)
        deleted = _create_post("deleted_rejection", other, moderation_status=Post.MODERATION_REJECTED,
                               visibility=Post.VISIBILITY_DRAFT, deleted_at=datetime.utcnow())
        RoomMuted.objects.create(user=self.user, room=room)

        for role in [User.ROLE_CURATOR, User.ROLE_MODERATOR, User.ROLE_GOD]:
            self.user.roles = [role]
            self.user.save()
            with self.subTest(role=role):
                response = self.client.get("/")
                self.assertEqual(
                    {p.id for p in response.context["moderation_posts"]}, {pending.id, own_pending.id},
                )
                feed_ids = {p.id for p in response.context["posts"]}
                self.assertIn(rejected.id, feed_ids)
                self.assertNotIn(draft.id, feed_ids)
                self.assertNotIn(deleted.id, feed_ids)
                self.assertNotIn(own_pending.id, feed_ids)
                self.assertNotIn(own_pending.id, [p.id for p in response.context["pinned_posts"]])

            with self.subTest(role=role, url="/all/new/"):
                response = self.client.get("/all/new/")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    {p.id for p in response.context["moderation_posts"]}, {pending.id, own_pending.id},
                )
                self.assertIn(rejected.id, [p.id for p in response.context["posts"]])

            for url in ["/post/", "/question/", "/label/other/", f"/room/{room.slug}/", "/all/top_week/"]:
                with self.subTest(role=role, url=url):
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(list(response.context["moderation_posts"]), [])
                    self.assertNotIn(rejected.id, [p.id for p in response.context["posts"]])
            self.assertTrue(rejected.can_view(self.user))

    def test_staff_feed_orderings_include_only_expected_moderation_posts(self):
        other = _create_user("ordering_moderation_author")
        approved = _create_post("ordering_approved", other)
        pending = _create_post(
            "ordering_pending", other, moderation_status=Post.MODERATION_PENDING,
            visibility=Post.VISIBILITY_LINK_ONLY,
        )
        rejected = _create_post(
            "ordering_rejected", other, moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT,
        )
        _create_post("ordering_draft", other, visibility=Post.VISIBILITY_DRAFT)
        _create_post(
            "ordering_withdrawn", other, moderation_status=Post.MODERATION_PENDING,
            visibility=Post.VISIBILITY_DRAFT,
        )
        _create_post(
            "ordering_deleted", other, moderation_status=Post.MODERATION_PENDING,
            visibility=Post.VISIBILITY_LINK_ONLY, deleted_at=datetime.utcnow(),
        )
        stale_rejected = _create_post(
            "ordering_stale_rejected", other, moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT,
        )
        Post.objects.filter(id=stale_rejected.id).update(
            last_activity_at=datetime.utcnow() - timedelta(days=8),
        )

        for role in [User.ROLE_CURATOR, User.ROLE_MODERATOR, User.ROLE_GOD]:
            self.user.roles = [role]
            self.user.save()

            for ordering in ["activity", "new", "hot", "top", "top_week", "top_month", "top_year"]:
                with self.subTest(role=role, ordering=ordering):
                    response = self.client.get(f"/all/{ordering}/")
                    self.assertEqual(response.status_code, 200)

                    if ordering in ["activity", "new"]:
                        self.assertEqual({post.id for post in response.context["posts"]}, {approved.id, rejected.id})
                        self.assertEqual({post.id for post in response.context["moderation_posts"]}, {pending.id})
                    else:
                        self.assertEqual({post.id for post in response.context["posts"]}, {approved.id})
                        self.assertEqual(list(response.context["moderation_posts"]), [])

    def test_author_pending_posts_stay_above_main_feed(self):
        room = _create_room("author_pending_room")
        RoomMuted.objects.create(user=self.user, room=room)
        pending = _create_post(
            "author_pending", self.user, room=room, is_room_only=True,
            moderation_status=Post.MODERATION_PENDING, visibility=Post.VISIBILITY_LINK_ONLY,
            published_at=datetime.utcnow() - timedelta(days=800),
        )
        pinned = _create_post(
            "author_pending_pinned", self.user, moderation_status=Post.MODERATION_PENDING,
            visibility=Post.VISIBILITY_LINK_ONLY, is_pinned_until=datetime.utcnow() + timedelta(days=1),
        )
        _create_post(
            "author_pending_draft", self.user, moderation_status=Post.MODERATION_PENDING,
            visibility=Post.VISIBILITY_DRAFT,
        )
        _create_post(
            "author_pending_deleted", self.user, moderation_status=Post.MODERATION_PENDING,
            visibility=Post.VISIBILITY_LINK_ONLY,
        ).delete()
        other = _create_user("other_pending_author")
        _create_post(
            "other_author_pending", other, moderation_status=Post.MODERATION_PENDING,
            visibility=Post.VISIBILITY_LINK_ONLY,
        )

        for url in ["/", "/?page=2", "/all/", "/all/activity/", "/all/new/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual({post.id for post in response.context["moderation_posts"]}, {pending.id, pinned.id})
                self.assertEqual(list(response.context["posts"]), [])
                self.assertEqual(list(response.context["pinned_posts"]), [])

        for url in ["/all/hot/", "/all/top/", "/post/", "/label/other/", f"/room/{room.slug}/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(list(response.context["moderation_posts"]), [])

    def test_author_sees_own_rejected_posts_in_main_feeds(self):
        rejected = _create_post(
            "own_rejection", self.user, moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT, published_at=None,
        )
        foreign = _create_post(
            "foreign_rejection", _create_user("foreign_rejection_author"),
            moderation_status=Post.MODERATION_REJECTED, visibility=Post.VISIBILITY_DRAFT,
        )
        deleted = _create_post(
            "deleted_own_rejection", self.user, moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT, deleted_at=datetime.utcnow(),
        )
        stale = _create_post(
            "stale_own_rejection", self.user, moderation_status=Post.MODERATION_REJECTED,
            visibility=Post.VISIBILITY_DRAFT,
        )
        Post.objects.filter(id=stale.id).update(last_activity_at=datetime.utcnow() - timedelta(days=8))

        for url in ["/", "/all/new/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                feed_ids = {post.id for post in response.context["posts"]}
                self.assertIn(rejected.id, feed_ids)
                self.assertNotIn(foreign.id, feed_ids)
                self.assertNotIn(deleted.id, feed_ids)
                self.assertNotIn(stale.id, feed_ids)

        for url in ["/post/", "/all/hot/", "/all/top/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertNotIn(rejected.id, [post.id for post in response.context["posts"]])

    def test_regular_users_cannot_see_moderation_queue_or_rejected_drafts(self):
        other = _create_user("private_rejection_author")
        rejected = _create_post("private_rejection", other, moderation_status=Post.MODERATION_REJECTED,
                                visibility=Post.VISIBILITY_DRAFT)
        _create_post("private_pending", other, moderation_status=Post.MODERATION_PENDING,
                     visibility=Post.VISIBILITY_LINK_ONLY)
        for url in ["/", "/post/", "/all/new/"]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(list(response.context["moderation_posts"]), [])
                self.assertEqual(list(response.context["posts"]), [])
        self.assertFalse(rejected.can_view(self.user))
        self.assertFalse(rejected.can_view(None))

    def test_republish_clears_rejection_attribution(self):
        post = _create_post("rejected_to_republish", self.user, moderation_status=Post.MODERATION_REJECTED,
                            moderation_data={"text": "Rendered rejection", "user": {"slug": self.user.slug}},
                            visibility=Post.VISIBILITY_DRAFT)
        post.publish()
        post.refresh_from_db()
        self.assertEqual(post.moderation_status, Post.MODERATION_PENDING)
        self.assertIsNone(post.moderation_data)

    def test_rejection_snapshot_survives_moderator_deletion(self):
        moderator = _create_user("departing_moderator")
        moderation_data = {
            "text": "Rendered rejection",
            "user": {"slug": moderator.slug, "avatar": moderator.get_avatar(), "full_name": moderator.full_name},
        }
        post = _create_post("moderator_deleted", self.user, moderation_status=Post.MODERATION_REJECTED,
                            moderation_data=moderation_data, visibility=Post.VISIBILITY_DRAFT)
        User.objects.filter(id=moderator.id).delete()
        post.refresh_from_db()
        self.assertEqual(post.moderation_data, moderation_data)
        self.assertEqual(post.moderation_status, Post.MODERATION_REJECTED)
