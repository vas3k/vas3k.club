from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import django
from django.conf import settings
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from django.http import Http404
from django.test import TestCase, override_settings

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from authn.helpers import is_safe_url, get_access_denied_reason
from authn.decorators.api import api
from authn.models.session import Code
from club.exceptions import (
    ApiAccessDenied, ApiAuthRequired, ApiException, ClubException, InvalidCode, RateLimitException,
)
from users.models.user import User


class IsSafeUrlTests(TestCase):

    def test_relative_path_is_safe(self):
        self.assertTrue(is_safe_url("/user/foo/"))
        self.assertTrue(is_safe_url("/auth/login/"))

    def test_absolute_url_same_host_is_safe(self):
        self.assertTrue(is_safe_url("http://127.0.0.1:8000/user/foo/"))

    @override_settings(APP_HOST="https://vas3k.club")
    def test_absolute_url_production_host_is_safe(self):
        self.assertTrue(is_safe_url("https://vas3k.club/user/foo/"))

    def test_external_url_is_rejected(self):
        self.assertFalse(is_safe_url("https://evil.com/phishing"))

    def test_host_prefix_bypass_is_rejected(self):
        self.assertFalse(is_safe_url("http://127.0.0.1:8000.evil.com/"))

    def test_protocol_relative_url_is_rejected(self):
        self.assertFalse(is_safe_url("//evil.com"))
        self.assertFalse(is_safe_url("///evil.com"))

    def test_javascript_uri_is_rejected(self):
        self.assertFalse(is_safe_url("javascript:alert(1)"))

    def test_data_uri_is_rejected(self):
        self.assertFalse(is_safe_url("data:text/html,<script>alert(1)</script>"))

    def test_empty_and_none_are_rejected(self):
        self.assertFalse(is_safe_url(""))
        self.assertFalse(is_safe_url(None))


class GetAccessDeniedReasonTests(TestCase):

    @staticmethod
    def _make_user(**overrides):
        return SimpleNamespace(**{
            "is_banned": False,
            "is_active_membership": True,
            "moderation_status": User.MODERATION_STATUS_APPROVED,
            **overrides,
        })

    def test_approved_active_user_allowed(self):
        self.assertIsNone(get_access_denied_reason(self._make_user()))

    def test_banned_user_denied(self):
        self.assertEqual(
            get_access_denied_reason(self._make_user(is_banned=True)), "banned"
        )

    def test_expired_membership_denied(self):
        self.assertEqual(
            get_access_denied_reason(self._make_user(is_active_membership=False)),
            "membership_expired",
        )

    def test_banned_takes_priority_over_expired(self):
        self.assertEqual(
            get_access_denied_reason(self._make_user(is_banned=True, is_active_membership=False)),
            "banned",
        )

    def test_intro_status_denied(self):
        user = self._make_user(moderation_status=User.MODERATION_STATUS_INTRO)
        self.assertEqual(get_access_denied_reason(user), "intro")

    def test_on_review_status_denied(self):
        user = self._make_user(moderation_status=User.MODERATION_STATUS_ON_REVIEW)
        self.assertEqual(get_access_denied_reason(user), "on_review")

    def test_rejected_status_denied(self):
        user = self._make_user(moderation_status=User.MODERATION_STATUS_REJECTED)
        self.assertEqual(get_access_denied_reason(user), "rejected")

    def test_deleted_status_not_checked(self):
        user = self._make_user(moderation_status=User.MODERATION_STATUS_DELETED)
        self.assertIsNone(get_access_denied_reason(user))


class ApiDecoratorAccessControlTests(TestCase):

    @staticmethod
    @api(require_auth=True)
    def _dummy_view(request):
        return {"ok": True}

    @staticmethod
    def _make_request(**user_overrides):
        return SimpleNamespace(
            me=GetAccessDeniedReasonTests._make_user(**user_overrides),
            headers={},
            GET={},
            COOKIES={},
        )

    def test_active_user_passes(self):
        result = self._dummy_view(self._make_request())
        self.assertEqual(result.status_code, 200)

    def test_banned_user_rejected(self):
        with self.assertRaises(ApiAccessDenied) as ctx:
            self._dummy_view(self._make_request(is_banned=True))
        self.assertEqual(ctx.exception.code, "banned")

    def test_expired_membership_rejected(self):
        with self.assertRaises(ApiAccessDenied) as ctx:
            self._dummy_view(self._make_request(is_active_membership=False))
        self.assertEqual(ctx.exception.code, "membership_expired")

    def test_on_review_user_rejected(self):
        with self.assertRaises(ApiAccessDenied) as ctx:
            self._dummy_view(self._make_request(
                moderation_status=User.MODERATION_STATUS_ON_REVIEW,
            ))
        self.assertEqual(ctx.exception.code, "on_review")


class ApiDecoratorResponseFormatTests(TestCase):

    @staticmethod
    def _make_request(**user_overrides):
        return SimpleNamespace(
            me=GetAccessDeniedReasonTests._make_user(**user_overrides),
            headers={},
            GET={},
            COOKIES={},
        )

    def test_dict_returns_json_response(self):
        @api(require_auth=True)
        def view(request):
            return {"key": "value"}

        result = view(self._make_request())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result["Content-Type"], "application/json")
        self.assertIn("value", result.content.decode())

    def test_str_returns_text_response(self):
        @api(require_auth=True)
        def view(request):
            return "plain text"

        result = view(self._make_request())
        self.assertEqual(result.status_code, 200)
        self.assertIn("text/plain", result["Content-Type"])
        self.assertEqual(result.content.decode(), "plain text")

    def test_http_response_returned_as_is(self):
        from django.http import HttpResponse

        @api(require_auth=True)
        def view(request):
            return HttpResponse("<html>ok</html>", content_type="text/html")

        result = view(self._make_request())
        self.assertEqual(result.status_code, 200)
        self.assertIn("text/html", result["Content-Type"])

    def test_dict_with_unicode(self):
        @api(require_auth=True)
        def view(request):
            return {"name": "Привет мир"}

        result = view(self._make_request())
        self.assertIn("Привет мир", result.content.decode())


class ApiDecoratorAuthTests(TestCase):

    @staticmethod
    def _make_request(headers=None, get_params=None, me=None):
        return SimpleNamespace(
            me=me,
            headers=headers or {},
            GET=get_params or {},
            COOKIES={},
        )

    @staticmethod
    def _make_user():
        return GetAccessDeniedReasonTests._make_user()

    @patch("authn.models.openid.OAuth2App.by_service_token")
    def test_service_token_authenticates(self, mock_by_service_token):
        owner = self._make_user()
        mock_app = MagicMock()
        mock_app.owner = owner
        mock_app.client_id = "test-client"
        mock_app.scope = "read write"
        mock_by_service_token.return_value = mock_app

        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request(headers={"X-Service-Token": "secret-token"})
        result = view(request)
        self.assertEqual(result.status_code, 200)
        self.assertIs(request.me, owner)
        self.assertIn("read", request.oauth_token.get_scopes())
        mock_by_service_token.assert_called_once_with("secret-token")

    @patch("authn.decorators.api.oauth2_token_validator")
    def test_oauth_authenticates(self, mock_validator):
        owner = self._make_user()
        mock_token = MagicMock()
        mock_token.user = owner
        mock_validator.acquire_token.return_value = mock_token

        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request(headers={"Authorization": "Bearer abc123"})
        result = view(request)
        self.assertEqual(result.status_code, 200)
        self.assertIs(request.me, owner)
        self.assertIs(request.oauth_token, mock_token)

    @patch("authn.decorators.api.oauth2_token_validator")
    @patch("authn.models.openid.OAuth2App.by_service_token")
    def test_service_token_priority_over_oauth(self, mock_by_service_token, mock_validator):
        owner = self._make_user()
        mock_app = MagicMock()
        mock_app.owner = owner
        mock_app.client_id = "test-client"
        mock_app.scope = "read"
        mock_by_service_token.return_value = mock_app

        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request(headers={
            "X-Service-Token": "secret-token",
            "Authorization": "Bearer abc123",
        })
        result = view(request)
        self.assertEqual(result.status_code, 200)
        self.assertIs(request.me, owner)
        mock_validator.acquire_token.assert_not_called()

    def test_http404_returns_api_not_found(self):
        @api(require_auth=True)
        def view(request):
            raise Http404("no such object")

        request = self._make_request(me=self._make_user())
        with self.assertRaises(ApiException) as ctx:
            view(request)
        self.assertEqual(ctx.exception.code, "not-found")
        self.assertEqual(ctx.exception.title, "Not found")

    def test_unhandled_exception_propagates(self):
        @api(require_auth=True)
        def view(request):
            raise RuntimeError("unexpected failure")

        request = self._make_request(me=self._make_user())
        with self.assertRaises(RuntimeError):
            view(request)

    @patch("authn.models.openid.OAuth2App.by_service_token")
    @patch("authn.decorators.api.log")
    def test_query_param_service_token_logs_warning(self, mock_log, mock_by_service_token):
        owner = self._make_user()
        mock_app = MagicMock()
        mock_app.owner = owner
        mock_app.client_id = "test-client"
        mock_app.scope = ""
        mock_by_service_token.return_value = mock_app

        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request(get_params={"service_token": "secret-token"})
        view(request)
        mock_log.warning.assert_called_once()

    @patch("authn.models.openid.OAuth2App.by_service_token")
    def test_invalid_service_token_raises_auth_required(self, mock_by_service_token):
        mock_by_service_token.return_value = None

        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request(headers={"X-Service-Token": "bad-token"})
        with self.assertRaises(ApiAuthRequired):
            view(request)

    @patch("authn.decorators.api.oauth2_token_validator")
    def test_oauth_missing_token_raises_auth_required(self, mock_validator):
        mock_validator.acquire_token.side_effect = MissingAuthorizationError()

        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request(headers={"Authorization": "Bearer bad"})
        with self.assertRaises(ApiAuthRequired):
            view(request)

    @patch("authn.decorators.api.oauth2_token_validator")
    def test_oauth_error_raises_auth_required(self, mock_validator):
        mock_validator.acquire_token.side_effect = OAuth2Error()

        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request(headers={"Authorization": "Bearer expired"})
        with self.assertRaises(ApiAuthRequired):
            view(request)

    def test_no_auth_raises_auth_required(self):
        @api(require_auth=True)
        def view(request):
            return {"ok": True}

        request = self._make_request()
        with self.assertRaises(ApiAuthRequired):
            view(request)

    def test_require_auth_false_skips_auth(self):
        @api(require_auth=False)
        def view(request):
            return {"ok": True}

        request = self._make_request()
        result = view(request)
        self.assertEqual(result.status_code, 200)

    def test_club_exception_wrapped_into_api_exception(self):
        @api(require_auth=True)
        def view(request):
            raise ClubException(code="test-error", title="Test")

        request = self._make_request(me=self._make_user())
        with self.assertRaises(ApiException) as ctx:
            view(request)
        self.assertEqual(ctx.exception.code, "test-error")

    def test_api_exception_reraised_as_is(self):
        @api(require_auth=True)
        def view(request):
            raise ApiException(code="custom", title="Custom error")

        request = self._make_request(me=self._make_user())
        with self.assertRaises(ApiException) as ctx:
            view(request)
        self.assertEqual(ctx.exception.code, "custom")
        self.assertEqual(ctx.exception.title, "Custom error")


class ModelCodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Set up data for the whole TestCase
        cls.new_user: User = User.objects.create(
            email="testemail@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
        )

    def test_create_code_positive(self):
        recipient = "success@a.com"

        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        self.assertEqual(code.recipient, recipient)
        self.assertEqual(self.new_user.id, code.user_id)
        self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)
        self.assertAlmostEqual(code.expires_at.second, (datetime.utcnow() + timedelta(minutes=15)).second, delta=5)

    def test_create_code_ratelimit(self):
        recipient = "ratelimit@a.com"

        # override the AUTH_MAX_CODE_TIMEDELTA setting
        with self.settings(AUTH_MAX_CODE_COUNT=1):
            code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
            self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)

            # second attempt should rise exception
            with self.assertRaises(RateLimitException):
                Code.create_for_user(user=self.new_user, recipient=recipient)

    def test_create_code_reset_ratelimit(self):
        recipient = "ratelimit@a.com"

        with self.settings(AUTH_MAX_CODE_COUNT=1):
            code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
            self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)

            # move creation time to deep enough past
            code.created_at = datetime.utcnow() - settings.AUTH_MAX_CODE_TIMEDELTA - timedelta(seconds=1)
            code.save()

            # no exception raises
            code = Code.create_for_user(user=self.new_user, recipient=recipient)
            self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)

    def test_check_code_positive(self):
        recipient = "success@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)

        user = Code.check_code(recipient=recipient, code=code.code)

        self.assertEqual(user.id, self.new_user.id)

    def test_check_code_which_is_incorrect(self):
        with self.assertRaises(InvalidCode):
            Code.check_code(recipient="failed@xxx.com", code="failed")

    def test_check_code_twice(self):
        recipient = "success@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        Code.check_code(recipient=recipient, code=code.code)  # activate first time

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient, code=code.code)

    def test_check_code_which_is_not_last_one(self):
        # issue few codes
        recipient = "fewcodes@a.com"
        code1: Code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        code2: Code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        # for stability test runs
        code2.created_at -= timedelta(seconds=1)
        code2.save()

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient, code=code2.code)

        # first one is successful
        user = Code.check_code(recipient=recipient, code=code1.code)
        self.assertEqual(user.id, self.new_user.id)

    def test_check_code_which_is_for_other_user(self):
        recipient_right = "true-user@a.com"
        recipient_wrong = "wrong-user@x.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient_right, length=settings.AUTH_CODE_LENGTH)

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient_wrong, code=code.code)

    def test_check_code_when_exceeded_attempts_count(self):
        recipient = "exceeded_attemts@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)

        # override the AUTH_MAX_CODE_TIMEDELTA setting
        with self.settings(AUTH_MAX_CODE_ATTEMPTS=1):
            # first attempt
            with self.assertRaises(InvalidCode):
                Code.check_code(recipient=recipient, code="wrong_attempt")

            # second attempt should rise ratelimit exception
            with self.assertRaises(RateLimitException):
                Code.check_code(recipient=recipient, code=code.code)

    def test_check_code_which_is_expired(self):
        recipient = "expired@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)
        code.expires_at = datetime.utcnow() - timedelta(seconds=1)
        code.save()

        with self.assertRaises(InvalidCode):
            Code.check_code(recipient=recipient, code=code.code)
