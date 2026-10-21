from django.test import RequestFactory, SimpleTestCase

from club.exceptions import ApiBadRequest
from common.api import API


class TestApiBody(SimpleTestCase):
    def test_form_values_are_available_to_api_validation(self):
        request = RequestFactory().post("/invites.json", {"reference": "form-reference"})

        self.assertEqual(API.parse_body(request), {"reference": "form-reference"})

    def test_json_values_preserve_types(self):
        request = RequestFactory().post(
            "/invites.json", {"telegram_user_id": 123, "reference": "json-reference"},
            content_type="application/json",
        )

        self.assertEqual(API.parse_body(request), {"telegram_user_id": 123, "reference": "json-reference"})

    def test_malformed_or_non_object_json_is_rejected(self):
        for body in [b"", b"{broken", b"[]", b"null", b"123", b'"text"', b"\xff"]:
            with self.subTest(body=body):
                request = RequestFactory().post(
                    "/invites.json", body, content_type="application/json", CONTENT_TYPE="application/json",
                )

                with self.assertRaises(ApiBadRequest):
                    API.parse_body(request)
