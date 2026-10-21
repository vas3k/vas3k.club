import json
from unittest.mock import Mock, patch
from urllib.parse import urlsplit

from django.http import JsonResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from authn.models.openid import OAuth2App, OAuth2Token
from club.exceptions import ApiAuthRequired, ApiException, RateLimitException
from debug.utils_for_tests import create_approved_user


class TestApiResponses(SimpleTestCase):
    def test_preserves_explicit_response_status_and_headers(self):
        request = RequestFactory().get("/example.json")
        request.me = None
        response = JsonResponse({"result": "ok"}, status=201)
        response["X-Result"] = "created"

        view = api(require_auth=False)(lambda request: response)
        result = view(request)

        self.assertEqual(result.status_code, 201)
        self.assertEqual(result["X-Result"], "created")
        self.assertEqual(json.loads(result.content), {"result": "ok"})

    def test_method_rejection_does_not_execute_mutation(self):
        request = RequestFactory().get("/example.json")
        request.me = None
        mutation = Mock(return_value={"success": True})
        view = api(require_auth=False)(require_http_methods(["POST"])(mutation))

        result = view(request)

        self.assertEqual(result.status_code, 405)
        self.assertEqual(result["Allow"], "POST")
        mutation.assert_not_called()

    def test_missing_authentication_does_not_execute_mutation(self):
        request = RequestFactory().post("/example.json")
        request.me = None
        mutation = Mock(return_value={"success": True})
        view = api()(mutation)

        with self.assertRaises(ApiAuthRequired):
            view(request)

        mutation.assert_not_called()

    def test_domain_error_preserves_code_and_recovery_data(self):
        request = RequestFactory().post("/example.json")
        request.me = None
        mutation = Mock(side_effect=RateLimitException(data={"saved_text": "unsent comment"}))
        view = api(require_auth=False)(mutation)

        with self.assertRaises(ApiException) as raised:
            view(request)

        self.assertEqual(raised.exception.code, "rate-limit")
        self.assertEqual(raised.exception.data, {"saved_text": "unsent comment"})

    @patch("authn.decorators.api.log.exception")
    def test_unexpected_failure_is_logged_without_exposing_details(self, log_exception):
        request = RequestFactory().get("/example.json")
        request.me = None

        @api(require_auth=False)
        def failing_view(request):
            raise ValueError("database password and private query")

        with self.assertRaises(ApiException) as raised:
            failing_view(request)

        self.assertEqual(raised.exception.code, "ValueError")
        self.assertNotIn("password", raised.exception.title)
        self.assertIsNone(raised.exception.message)
        log_exception.assert_called_once()


class TestOpenIDDiscoveryUserinfo(TestCase):
    def test_published_userinfo_endpoint_accepts_bearer_without_exposing_contact_data(self):
        user = create_approved_user("discovery_user", telegram_data={"username": "private_contact"})
        app = OAuth2App.objects.create(name="Discovery client", owner=user, scope="openid")
        token = OAuth2Token.objects.create(
            user=user, client_id=app.client_id, token_type="Bearer", scope="openid",
            access_token="discovery-access-token", refresh_token="discovery-refresh-token", expires_in=3600,
        )

        discovery = self.client.get(reverse("openid_well_known_configuration"))

        self.assertEqual(discovery.status_code, 200)
        userinfo_path = urlsplit(discovery.json()["userinfo_endpoint"]).path
        self.assertEqual(userinfo_path, "/user/me.json")
        self.assertEqual(reverse("api_profile", args=["me"]), userinfo_path)

        response = self.client.get(userinfo_path, headers={"Authorization": f"Bearer {token.access_token}"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()["user"]
        self.assertEqual(payload["id"], str(user.id))
        self.assertNotIn("email", payload)
        self.assertNotIn("telegram", payload)
