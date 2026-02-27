from django.core.cache import cache
from django.test import TestCase

from godmode.models import CLUB_SETTINGS_CACHE_KEY, ClubSettings


class ClubSettingsCacheTest(TestCase):
    def setUp(self):
        cache.delete(CLUB_SETTINGS_CACHE_KEY)

    def tearDown(self):
        cache.delete(CLUB_SETTINGS_CACHE_KEY)

    def test_get_returns_value(self):
        ClubSettings.set("k", "v")
        self.assertEqual(ClubSettings.get("k"), "v")

    def test_get_returns_default_for_missing(self):
        self.assertEqual(ClubSettings.get("nope", "d"), "d")

    def test_get_hits_cache_on_second_call(self):
        ClubSettings.set("k", "v")
        ClubSettings.get("k")  # prime the cache
        with self.assertNumQueries(0):
            result = ClubSettings.get("k")
        self.assertEqual(result, "v")

    def test_set_invalidates_cache(self):
        ClubSettings.set("k", "v1")
        ClubSettings.get("k")  # prime the cache
        ClubSettings.set("k", "v2")
        self.assertEqual(ClubSettings.get("k"), "v2")

    def test_save_invalidates_cache(self):
        obj = ClubSettings.set("k", "v1")
        ClubSettings.get("k")  # prime the cache
        obj.value = "new"
        obj.save()
        self.assertEqual(ClubSettings.get("k"), "new")

    def test_delete_invalidates_cache(self):
        obj = ClubSettings.set("k", "v")
        ClubSettings.get("k")  # prime the cache
        obj.delete()
        self.assertEqual(ClubSettings.get("k", "d"), "d")

    def test_get_normalizes_code(self):
        ClubSettings.set("mykey", "v")
        self.assertEqual(ClubSettings.get(" MYKEY "), "v")

    def test_set_normalizes_code(self):
        ClubSettings.set(" MYKEY ", "v")
        self.assertEqual(ClubSettings.get("mykey"), "v")

    def test_multiple_settings_loaded_in_one_query(self):
        ClubSettings.set("a", "1")
        ClubSettings.set("b", "2")
        ClubSettings.set("c", "3")
        cache.delete(CLUB_SETTINGS_CACHE_KEY)
        with self.assertNumQueries(1):
            a = ClubSettings.get("a")
            b = ClubSettings.get("b")
            c = ClubSettings.get("c")
        self.assertEqual(a, "1")
        self.assertEqual(b, "2")
        self.assertEqual(c, "3")

    def test_get_returns_none_by_default(self):
        self.assertIsNone(ClubSettings.get("nope"))

    def test_get_returns_none_value_not_default(self):
        ClubSettings.set("k", None)
        result = ClubSettings.get("k", "fallback")
        self.assertIsNone(result)

    def test_empty_table_is_cached(self):
        ClubSettings.get("anything")  # prime cache with empty dict
        with self.assertNumQueries(0):
            result = ClubSettings.get("anything", "d")
        self.assertEqual(result, "d")
