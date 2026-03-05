import json
from unittest.mock import patch

from django.test import TestCase

from users.models.geo import geo_coordinates
from users.templatetags.users import users_geo_json


class TestGeoCoordinates(TestCase):

    def test_returns_none_for_none(self):
        self.assertIsNone(geo_coordinates(None))

    def test_returns_none_for_empty_dict(self):
        self.assertIsNone(geo_coordinates({}))

    def test_returns_none_when_latitude_missing(self):
        self.assertIsNone(geo_coordinates({"longitude": 13.4}))

    def test_returns_none_when_longitude_missing(self):
        self.assertIsNone(geo_coordinates({"latitude": 52.5}))

    def test_handles_zero_latitude(self):
        result = geo_coordinates({"latitude": 0.0, "longitude": 13.4, "precise": True})
        self.assertEqual(result, (0.0, 13.4))

    def test_handles_zero_longitude(self):
        result = geo_coordinates({"latitude": 52.5, "longitude": 0.0, "precise": True})
        self.assertEqual(result, (52.5, 0.0))

    def test_precise_returns_exact_coordinates(self):
        geo = {"latitude": 52.52, "longitude": 13.405, "precise": True}
        self.assertEqual(geo_coordinates(geo), (52.52, 13.405))

    def test_non_precise_applies_offset(self):
        geo = {"latitude": 52.52, "longitude": 13.405}
        with patch("users.models.geo.random.uniform", return_value=0.05):
            result = geo_coordinates(geo)
        self.assertEqual(result, (52.57, 13.455))

    def test_non_precise_offset_range(self):
        geo = {"latitude": 50.0, "longitude": 10.0}
        for _ in range(100):
            lat, lng = geo_coordinates(geo)
            self.assertAlmostEqual(lat, 50.0, delta=0.12)
            self.assertAlmostEqual(lng, 10.0, delta=0.25)


class TestUsersGeoJson(TestCase):

    def test_builds_valid_geojson(self):
        users = [
            ("alice", "https://img/a.jpg", {"latitude": 52.52, "longitude": 13.4, "precise": True}),
        ]
        result = json.loads(users_geo_json(users))
        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(result["id"], "user-markers")
        self.assertEqual(len(result["features"]), 1)

        feature = result["features"][0]
        self.assertEqual(feature["type"], "Feature")
        self.assertEqual(feature["properties"]["id"], "alice")
        self.assertEqual(feature["properties"]["url"], "/user/alice/")
        self.assertEqual(feature["properties"]["avatar"], "https://img/a.jpg")
        self.assertEqual(feature["geometry"]["type"], "Point")
        self.assertEqual(feature["geometry"]["coordinates"], [13.4, 52.52])

    def test_skips_entries_with_no_coordinates(self):
        users = [
            ("alice", None, {"latitude": 52.52, "longitude": 13.4, "precise": True}),
            ("bob", None, {}),
            ("carol", None, None),
        ]
        result = json.loads(users_geo_json(users))
        self.assertEqual(len(result["features"]), 1)
        self.assertEqual(result["features"][0]["properties"]["id"], "alice")

    def test_empty_input(self):
        result = json.loads(users_geo_json([]))
        self.assertEqual(result["features"], [])

    def test_avatar_null_when_none(self):
        users = [
            ("alice", None, {"latitude": 1.0, "longitude": 2.0, "precise": True}),
        ]
        result = json.loads(users_geo_json(users))
        self.assertIsNone(result["features"][0]["properties"]["avatar"])

    def test_coordinates_order_is_lng_lat(self):
        users = [
            ("alice", None, {"latitude": 55.0, "longitude": 37.0, "precise": True}),
        ]
        result = json.loads(users_geo_json(users))
        coords = result["features"][0]["geometry"]["coordinates"]
        self.assertEqual(coords, [37.0, 55.0])  # GeoJSON: [lng, lat]
