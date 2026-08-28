from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.conf import settings
from django.test import TestCase, override_settings, RequestFactory

from authn.helpers import is_safe_url, get_access_denied_reason, authorized_user_with_session
from authn.decorators.api import api
from authn.models.session import Code, Session
from club.exceptions import ApiAccessDenied, ApiAuthRequired, RateLimitException, InvalidCode
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


class AuthorizedUserWithSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user: User = User.objects.create(
            email="auth_session@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
        )

    def setUp(self):
        self.factory = RequestFactory()

    def _request(self, token, ip="8.8.8.8", useragent="Mozilla/5.0 TestAgent"):
        request = self.factory.get("/", HTTP_USER_AGENT=useragent, HTTP_X_REAL_IP=ip)
        request.COOKIES["token"] = token
        return request

    def test_backfills_ip_and_useragent_on_valid_session(self):
        session = Session.create_for_user(self.user)

        user, result = authorized_user_with_session(self._request(session.token))

        self.assertEqual(user.id, self.user.id)
        self.assertEqual(result.ipaddress, "8.8.8.8")
        self.assertEqual(result.useragent, "Mozilla/5.0 TestAgent")
        session.refresh_from_db()
        self.assertEqual(session.ipaddress, "8.8.8.8")
        self.assertEqual(session.useragent, "Mozilla/5.0 TestAgent")

    def test_does_not_overwrite_existing_ip_and_useragent(self):
        session = Session.create_for_user(
            self.user,
            ipaddress="1.1.1.1",
            useragent="OldAgent/1.0",
        )

        _, result = authorized_user_with_session(self._request(session.token))

        self.assertEqual(result.ipaddress, "1.1.1.1")
        self.assertEqual(result.useragent, "OldAgent/1.0")
        session.refresh_from_db()
        self.assertEqual(session.ipaddress, "1.1.1.1")
        self.assertEqual(session.useragent, "OldAgent/1.0")

    def test_backfills_only_missing_fields(self):
        session = Session.create_for_user(self.user, ipaddress="1.1.1.1")

        _, result = authorized_user_with_session(self._request(session.token))

        self.assertEqual(result.ipaddress, "1.1.1.1")
        self.assertEqual(result.useragent, "Mozilla/5.0 TestAgent")

    def test_does_not_backfill_expired_session(self):
        session = Session.create_for_user(self.user)
        session.expires_at = datetime.utcnow() - timedelta(seconds=1)
        session.save()

        user, result = authorized_user_with_session(self._request(session.token))

        self.assertIsNone(user)
        self.assertIsNone(result)
        session.refresh_from_db()
        self.assertIsNone(session.ipaddress)
        self.assertIsNone(session.useragent)


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


class ApiDecoratorAuthResolutionTests(TestCase):
    """Tests that auth is resolved before require_auth check,
    so require_auth=False endpoints can still identify the user."""

    @staticmethod
    @api(require_auth=False)
    def _public_view(request):
        return {"has_user": request.me is not None}

    @staticmethod
    @api(require_auth=True)
    def _private_view(request):
        return {"ok": True}

    @staticmethod
    def _make_request(me=None, headers=None, get_params=None):
        return SimpleNamespace(
            me=me,
            headers=headers or {},
            GET=get_params or {},
            COOKIES={},
        )

    def test_public_endpoint_anonymous_succeeds(self):
        """require_auth=False with no credentials should succeed."""
        request = self._make_request()
        result = self._public_view(request)
        self.assertEqual(result.status_code, 200)

    @patch("authn.decorators.api.OAuth2Token")
    @patch("authn.decorators.api.app_by_service_token")
    def test_public_endpoint_resolves_service_token(self, mock_app_by_token, mock_token_cls):
        owner = GetAccessDeniedReasonTests._make_user()
        mock_app = MagicMock()
        mock_app.owner = owner
        mock_app.client_id = "test-client"
        mock_app.scope = "all"
        mock_app_by_token.return_value = mock_app
        mock_token_cls.return_value = MagicMock()

        request = self._make_request(
            headers={"X-Service-Token": "valid-token"},
        )
        result = self._public_view(request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(request.me, owner)
        self.assertIsNotNone(request.oauth_token)
        mock_app_by_token.assert_called_once_with("valid-token")

    @patch("authn.decorators.api.app_by_service_token")
    def test_public_endpoint_invalid_service_token_raises(self, mock_app_by_token):
        """Invalid service token should raise even on require_auth=False endpoints."""
        mock_app_by_token.return_value = None

        request = self._make_request(
            headers={"X-Service-Token": "bad-token"},
        )
        with self.assertRaises(ApiAuthRequired):
            self._public_view(request)

    @patch("authn.decorators.api.oauth2_token_validator")
    def test_public_endpoint_resolves_oauth_token(self, mock_validator):
        owner = GetAccessDeniedReasonTests._make_user()
        mock_token = MagicMock()
        mock_token.user = owner
        mock_validator.acquire_token.return_value = mock_token

        request = self._make_request(
            headers={"Authorization": "Bearer test-token"},
        )
        result = self._public_view(request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(request.me, owner)
        self.assertEqual(request.oauth_token, mock_token)

    def test_private_endpoint_no_auth_raises(self):
        """require_auth=True with no credentials should raise ApiAuthRequired."""
        request = self._make_request()
        with self.assertRaises(ApiAuthRequired):
            self._private_view(request)

    @patch("authn.decorators.api.OAuth2Token")
    @patch("authn.decorators.api.app_by_service_token")
    def test_service_token_via_query_param(self, mock_app_by_token, mock_token_cls):
        """Service token passed as query param should also be resolved."""
        owner = GetAccessDeniedReasonTests._make_user()
        mock_app = MagicMock()
        mock_app.owner = owner
        mock_app.client_id = "test-client"
        mock_app.scope = "all"
        mock_app_by_token.return_value = mock_app
        mock_token_cls.return_value = MagicMock()

        request = self._make_request(
            get_params={"service_token": "valid-token"},
        )
        result = self._public_view(request)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(request.me, owner)
        mock_app_by_token.assert_called_once_with("valid-token")


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

        code = Code.create_for_user(
            user=self.new_user,
            recipient=recipient,
            length=settings.AUTH_CODE_LENGTH,
            ipaddress="1.2.3.4",
            useragent="TestAgent/1.0",
        )
        self.assertEqual(code.recipient, recipient)
        self.assertEqual(self.new_user.id, code.user_id)
        self.assertEqual(len(code.code), settings.AUTH_CODE_LENGTH)
        self.assertRegex(code.code, r"^[A-Z0-9]+$")
        self.assertEqual(code.ipaddress, "1.2.3.4")
        self.assertEqual(code.useragent, "TestAgent/1.0")
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

    def test_create_code_ip_ratelimit(self):
        ipaddress = "10.0.0.1"

        with self.settings(AUTH_MAX_CODE_COUNT_PER_IP=1, AUTH_MAX_CODE_COUNT=10):
            code = Code.create_for_user(
                user=self.new_user,
                recipient="first@a.com",
                ipaddress=ipaddress,
            )
            self.assertEqual(code.ipaddress, ipaddress)

            with self.assertRaises(RateLimitException):
                Code.create_for_user(
                    user=self.new_user,
                    recipient="second@a.com",
                    ipaddress=ipaddress,
                )

    def test_create_code_ip_ratelimit_does_not_affect_other_ips(self):
        with self.settings(AUTH_MAX_CODE_COUNT_PER_IP=1, AUTH_MAX_CODE_COUNT=10):
            Code.create_for_user(
                user=self.new_user,
                recipient="first@a.com",
                ipaddress="10.0.0.1",
            )
            code = Code.create_for_user(
                user=self.new_user,
                recipient="second@a.com",
                ipaddress="10.0.0.2",
            )
            self.assertEqual(code.ipaddress, "10.0.0.2")

    def test_create_code_ip_ratelimit_skipped_without_ip(self):
        with self.settings(AUTH_MAX_CODE_COUNT_PER_IP=1, AUTH_MAX_CODE_COUNT=10):
            Code.create_for_user(user=self.new_user, recipient="first@a.com")
            code = Code.create_for_user(user=self.new_user, recipient="second@a.com")
            self.assertIsNone(code.ipaddress)

    def test_create_code_reset_ip_ratelimit(self):
        ipaddress = "10.0.0.1"

        with self.settings(AUTH_MAX_CODE_COUNT_PER_IP=1, AUTH_MAX_CODE_COUNT=10):
            code = Code.create_for_user(
                user=self.new_user,
                recipient="first@a.com",
                ipaddress=ipaddress,
            )
            code.created_at = datetime.utcnow() - settings.AUTH_MAX_CODE_TIMEDELTA - timedelta(seconds=1)
            code.save()

            code = Code.create_for_user(
                user=self.new_user,
                recipient="second@a.com",
                ipaddress=ipaddress,
            )
            self.assertEqual(code.ipaddress, ipaddress)

    def test_create_code_global_ratelimit(self):
        with self.settings(AUTH_MAX_CODE_COUNT_TOTAL=1, AUTH_MAX_CODE_COUNT=10, AUTH_MAX_CODE_COUNT_PER_IP=10):
            Code.create_for_user(
                user=self.new_user,
                recipient="first@a.com",
                ipaddress="10.0.0.1",
            )
            with self.assertRaises(RateLimitException):
                Code.create_for_user(
                    user=self.new_user,
                    recipient="second@a.com",
                    ipaddress="10.0.0.2",
                )

    def test_create_code_reset_global_ratelimit(self):
        with self.settings(AUTH_MAX_CODE_COUNT_TOTAL=1, AUTH_MAX_CODE_COUNT=10, AUTH_MAX_CODE_COUNT_PER_IP=10):
            code = Code.create_for_user(
                user=self.new_user,
                recipient="first@a.com",
                ipaddress="10.0.0.1",
            )
            code.created_at = datetime.utcnow() - settings.AUTH_MAX_CODE_TIMEDELTA - timedelta(seconds=1)
            code.save()

            code = Code.create_for_user(
                user=self.new_user,
                recipient="second@a.com",
                ipaddress="10.0.0.2",
            )
            self.assertEqual(code.recipient, "second@a.com")

    def test_check_code_positive(self):
        recipient = "success@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)

        user = Code.check_code(recipient=recipient, code=code.code)

        self.assertEqual(user.id, self.new_user.id)

    def test_check_code_is_case_insensitive(self):
        recipient = "case@a.com"
        code = Code.create_for_user(user=self.new_user, recipient=recipient, length=settings.AUTH_CODE_LENGTH)

        user = Code.check_code(recipient=recipient, code=code.code.lower())
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


class ModelSessionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.new_user: User = User.objects.create(
            email="session@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
        )

    def test_create_session_stores_ip_and_useragent(self):
        session = Session.create_for_user(
            self.new_user,
            ipaddress="1.2.3.4",
            useragent="TestAgent/1.0",
        )
        self.assertEqual(session.user_id, self.new_user.id)
        self.assertEqual(session.ipaddress, "1.2.3.4")
        self.assertEqual(session.useragent, "TestAgent/1.0")

    def test_create_session_without_ip_and_useragent(self):
        session = Session.create_for_user(self.new_user)
        self.assertIsNone(session.ipaddress)
        self.assertIsNone(session.useragent)
