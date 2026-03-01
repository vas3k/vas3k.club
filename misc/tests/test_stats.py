from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse

from badges.models import Badge, UserBadge
from debug.helpers import HelperClient
from posts.tests.test_views import ModelCreator
from users.models.user import User


class StatsViewTests(TestCase):
    def setUp(self) -> None:
        self.creator = ModelCreator()
        self.user = self.creator.create_user()
        self.client = HelperClient(user=self.user)
        self.client.authorise()

    def _create_badge_for_user(
        self,
        user: User,
        badge_code: str,
        from_user: User | None = None,
        price_days: int = 10,
    ) -> UserBadge:
        badge, _ = Badge.objects.get_or_create(
            code=badge_code,
            defaults={"title": badge_code, "price_days": price_days},
        )
        return UserBadge.objects.create(
            badge=badge,
            from_user=from_user or self.user,
            to_user=user,
        )

    def test_stats_page_loads(self) -> None:
        response = self.client.get(reverse("stats"))
        self.assertEqual(response.status_code, 200)

    def test_top_badges_ordered_by_sum_price(self) -> None:
        """Users in top_badges are ordered by total badge price descending."""
        user_low = self.creator.create_user()
        user_high = self.creator.create_user()

        self._create_badge_for_user(user_low, "cheap", price_days=10)
        self._create_badge_for_user(user_high, "expensive", price_days=50)

        response = self.client.get(reverse("stats"))
        top_badges = response.context["top_badges"]

        self.assertEqual(top_badges[0].id, user_high.id)
        self.assertEqual(top_badges[1].id, user_low.id)

    def test_top_badges_contains_user_data_and_badges(self) -> None:
        """Each user in top_badges has slug, full_name, and prefetched to_badges with badge."""
        target = self.creator.create_user()
        self._create_badge_for_user(target, "badge_a")
        self._create_badge_for_user(target, "badge_b")

        response = self.client.get(reverse("stats"))
        top_badges = response.context["top_badges"]

        user = next(u for u in top_badges if u.id == target.id)
        self.assertEqual(user.slug, target.slug)
        self.assertEqual(user.full_name, target.full_name)

        badges = list(user.to_badges.all())
        self.assertEqual(len(badges), 2)

        badge_codes = {b.badge.code for b in badges}
        self.assertEqual(badge_codes, {"badge_a", "badge_b"})

    def test_top_badges_renders_in_template(self) -> None:
        """Badge codes and user names appear in rendered HTML."""
        target = self.creator.create_user()
        self._create_badge_for_user(target, "star_badge")

        response = self.client.get(reverse("stats"))

        content = response.content.decode(response.charset)
        self.assertIn(target.full_name, content)
        self.assertIn("star_badge.png", content)

    def test_top_badges_excludes_non_registered_users(self) -> None:
        """Deleted/non-approved users are filtered out of top_badges."""
        deleted_user = self.creator.create_user()
        deleted_user.moderation_status = "rejected"
        deleted_user.save()
        self._create_badge_for_user(deleted_user, "badge_x")

        response = self.client.get(reverse("stats"))
        top_badges = response.context["top_badges"]

        user_ids = [u.id for u in top_badges]
        self.assertNotIn(deleted_user.id, user_ids)

    def test_top_badges_limited_to_15(self) -> None:
        """top_badges returns at most 15 users."""
        users = [self.creator.create_user() for _ in range(20)]
        for i, user in enumerate(users):
            self._create_badge_for_user(user, f"badge_{i}")

        response = self.client.get(reverse("stats"))
        top_badges = response.context["top_badges"]

        self.assertLessEqual(len(top_badges), 15)

    def test_top_badges_query_count_stable(self) -> None:
        """Query count must not grow with the number of badged users."""
        users_small = [self.creator.create_user() for _ in range(3)]
        for i, user in enumerate(users_small):
            self._create_badge_for_user(user, f"badge_s_{i}")

        self.client.get(reverse("stats"))
        with CaptureQueriesContext(connection) as ctx_small:
            self.client.get(reverse("stats"))
        count_small = len(ctx_small.captured_queries)

        users_large = [self.creator.create_user() for _ in range(10)]
        for i, user in enumerate(users_large):
            for j in range(i + 1):
                self._create_badge_for_user(user, f"badge_l_{j}")

        self.client.get(reverse("stats"))
        with CaptureQueriesContext(connection) as ctx_large:
            self.client.get(reverse("stats"))
        count_large = len(ctx_large.captured_queries)

        self.assertEqual(
            count_small, count_large,
            f"Query count grew from {count_small} to {count_large} — likely N+1.\n"
            + "\n".join(q["sql"][:120] for q in ctx_large.captured_queries),
        )
