from datetime import datetime, timedelta

from django.db.models import Count
from django.test import TestCase

from tags.models import Tag, UserTag
from users.models.user import User

_SLUG_PREFIX = "tpeople_"


def _create_user(suffix, **kwargs):
    slug = f"{_SLUG_PREFIX}{suffix}"
    defaults = dict(
        email=f"{slug}@test.com",
        full_name=slug,
        membership_started_at=datetime.now() - timedelta(days=5),
        membership_expires_at=datetime.now() + timedelta(days=5),
        moderation_status=User.MODERATION_STATUS_APPROVED,
    )
    defaults.update(kwargs)
    return User.objects.create(slug=slug, **defaults)


def _test_users():
    return User.objects.filter(slug__startswith=_SLUG_PREFIX)


class TestTagsWithStats(TestCase):

    def test_returns_correct_user_counts_per_tag(self):
        tag_a = Tag.objects.create(code="tpeople_a", group=Tag.GROUP_TECH, name="Tag A", is_visible=True)
        tag_b = Tag.objects.create(code="tpeople_b", group=Tag.GROUP_TECH, name="Tag B", is_visible=True)
        Tag.objects.create(code="tpeople_c", group=Tag.GROUP_TECH, name="Tag C", is_visible=True)

        u1 = _create_user("u1")
        u2 = _create_user("u2")
        u3 = _create_user("u3")

        UserTag.objects.create(user=u1, tag=tag_a, name=tag_a.name)
        UserTag.objects.create(user=u2, tag=tag_a, name=tag_a.name)
        UserTag.objects.create(user=u3, tag=tag_a, name=tag_a.name)
        UserTag.objects.create(user=u1, tag=tag_b, name=tag_b.name)
        UserTag.objects.create(user=u2, tag=tag_b, name=tag_b.name)

        tags = {t.code: t.user_count for t in Tag.tags_with_stats()}
        self.assertEqual(tags["tpeople_a"], 3)
        self.assertEqual(tags["tpeople_b"], 2)
        self.assertEqual(tags["tpeople_c"], 0)

    def test_executes_in_single_query(self):
        Tag.objects.create(code="tpeople_x", group=Tag.GROUP_TECH, name="Tag X", is_visible=True)

        with self.assertNumQueries(1):
            list(Tag.tags_with_stats())

    def test_uses_orm_annotate_not_raw_sql(self):
        Tag.objects.create(code="tpeople_y", group=Tag.GROUP_TECH, name="Tag Y", is_visible=True)

        qs = Tag.tags_with_stats()
        sql = str(qs.query).lower()
        self.assertNotIn("select count(*) from user_tags", sql)


class TestActiveCountriesFiltering(TestCase):

    def test_excludes_empty_country_strings(self):
        _create_user("u1", country="TestCountry_X")
        _create_user("u2", country="TestCountry_X")
        _create_user("u3", country="")
        _create_user("u4", country=None)

        active_countries = (
            _test_users()
            .filter(country__isnull=False)
            .exclude(country="")
            .values("country")
            .annotate(country_count=Count("country"))
            .order_by("-country_count")
        )

        country_names = [c["country"] for c in active_countries]
        self.assertIn("TestCountry_X", country_names)
        self.assertNotIn("", country_names)
        self.assertEqual(len(country_names), 1)
