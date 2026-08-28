from unittest.mock import patch

from django.test import Client, TestCase, override_settings, RequestFactory
from django.urls import reverse

from authn.models.session import Session
from debug.utils_for_tests import create_approved_user, login
from users.views.settings import request_data


class TestUserSettingsViews(TestCase):
    def setUp(self):
        self.user = create_approved_user("settings_owner")
        self.other = create_approved_user("settings_other")
        self.client = Client()
        self.factory = RequestFactory()

    def test_non_owner_cannot_access_edit_notifications(self):
        login(self.client, self.other)

        response = self.client.get(reverse("edit_notifications", args=[self.user.slug]))

        self.assertEqual(response.status_code, 404)

    def test_edit_account_regenerate_changes_secret_hash(self):
        login(self.client, self.user)
        before = self.user.secret_hash

        response = self.client.post(reverse("edit_account", args=[self.user.slug]), data={"regenerate": "1"})

        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.secret_hash, before)

    def test_request_data_get_redirects_to_edit_data(self):
        login(self.client, self.user)

        response = self.client.get(reverse("request_user_data", args=[self.user.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("edit_data", args=[self.user.slug]))

    @override_settings(DEBUG=False)
    @patch("users.views.settings.async_task")
    @patch("users.views.settings.DataRequests.register_archive_request")
    def test_request_data_post_enqueues_async_job(self, mock_register, mock_async_task):
        login(self.client, self.user)

        response = self.client.post(reverse("request_user_data", args=[self.user.slug]))

        self.assertEqual(response.status_code, 200)
        mock_register.assert_called_once_with(self.user)
        mock_async_task.assert_called_once()

    @patch("users.views.settings.settings.DEBUG", True)
    @patch("users.views.settings.generate_data_archive")
    @patch("users.views.settings.DataRequests.register_archive_request")
    def test_request_data_post_calls_sync_generator_in_debug(self, mock_register, mock_generate):
        request = self.factory.post(reverse("request_user_data", args=[self.user.slug]))
        request.me = self.user

        response = request_data(request, self.user.slug)
        self.assertEqual(response.status_code, 200)
        mock_register.assert_called_once_with(self.user)
        mock_generate.assert_called_once_with(self.user)


class TestUserSessionsSettings(TestCase):
    def setUp(self):
        self.user = create_approved_user("sessions_owner")
        self.other = create_approved_user("sessions_other")
        self.client = Client()

    def test_settings_index_contains_sessions_link(self):
        login(self.client, self.user)

        response = self.client.get(reverse("profile_settings", args=[self.user.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Сессии")
        self.assertContains(response, reverse("edit_sessions", args=[self.user.slug]))

    def test_non_owner_cannot_access_sessions(self):
        login(self.client, self.other)

        response = self.client.get(reverse("edit_sessions", args=[self.user.slug]))

        self.assertEqual(response.status_code, 404)

    def test_lists_sessions_with_ip_browser_and_time(self):
        login(self.client, self.user)
        Session.create_for_user(
            self.user,
            ipaddress="203.0.113.10",
            useragent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        response = self.client.get(reverse("edit_sessions", args=[self.user.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "203.0.113.10")
        self.assertContains(response, "Chrome 120")
        self.assertContains(response, "fa-globe")
        self.assertContains(response, "fa-trash")

    def test_marks_current_session_by_token(self):
        login(self.client, self.user)

        response = self.client.get(reverse("edit_sessions", args=[self.user.slug]))

        self.assertContains(response, "(это устройство)")

    def test_does_not_mark_other_session_as_current(self):
        login(self.client, self.user)
        Session.create_for_user(self.user, ipaddress="203.0.113.10")

        response = self.client.get(reverse("edit_sessions", args=[self.user.slug]))

        self.assertContains(response, "(это устройство)", count=1)

    def test_deactivate_session_deletes_it(self):
        login(self.client, self.user)
        other_session = Session.create_for_user(self.user, ipaddress="198.51.100.20")

        response = self.client.post(
            reverse("deactivate_session", args=[self.user.slug, other_session.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("edit_sessions", args=[self.user.slug]))
        self.assertFalse(Session.objects.filter(id=other_session.id).exists())
        self.assertTrue(Session.objects.filter(user=self.user).exists())

    def test_deactivate_current_session_logs_out(self):
        login(self.client, self.user)
        current = Session.objects.get(token=self.client.cookies["token"].value)

        response = self.client.post(
            reverse("deactivate_session", args=[self.user.slug, current.id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("index"))
        self.assertFalse(Session.objects.filter(id=current.id).exists())

    def test_cannot_deactivate_another_users_session(self):
        login(self.client, self.user)
        foreign = Session.create_for_user(self.other, ipaddress="192.0.2.1")

        response = self.client.post(
            reverse("deactivate_session", args=[self.user.slug, foreign.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(Session.objects.filter(id=foreign.id).exists())

    def test_deactivate_rejects_get(self):
        login(self.client, self.user)
        session = Session.objects.get(token=self.client.cookies["token"].value)

        response = self.client.get(
            reverse("deactivate_session", args=[self.user.slug, session.id])
        )

        self.assertEqual(response.status_code, 405)

    def test_sessions_page_contains_deactivate_others_button(self):
        login(self.client, self.user)
        Session.create_for_user(self.user, ipaddress="198.51.100.20")

        response = self.client.get(reverse("edit_sessions", args=[self.user.slug]))

        self.assertContains(response, "Завершить все, кроме активной")
        self.assertContains(response, reverse("deactivate_other_sessions", args=[self.user.slug]))

    def test_sessions_page_hides_deactivate_others_button_for_single_session(self):
        login(self.client, self.user)

        response = self.client.get(reverse("edit_sessions", args=[self.user.slug]))

        self.assertNotContains(response, "Завершить все, кроме активной")

    def test_deactivate_other_sessions_keeps_current(self):
        login(self.client, self.user)
        current = Session.objects.get(token=self.client.cookies["token"].value)
        other_a = Session.create_for_user(self.user, ipaddress="198.51.100.20")
        other_b = Session.create_for_user(self.user, ipaddress="203.0.113.10")

        response = self.client.post(reverse("deactivate_other_sessions", args=[self.user.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("edit_sessions", args=[self.user.slug]))
        self.assertTrue(Session.objects.filter(id=current.id).exists())
        self.assertFalse(Session.objects.filter(id=other_a.id).exists())
        self.assertFalse(Session.objects.filter(id=other_b.id).exists())

    def test_deactivate_other_sessions_does_not_touch_another_user(self):
        login(self.client, self.user)
        foreign = Session.create_for_user(self.other, ipaddress="192.0.2.1")
        Session.create_for_user(self.user, ipaddress="198.51.100.20")

        response = self.client.post(reverse("deactivate_other_sessions", args=[self.user.slug]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Session.objects.filter(id=foreign.id).exists())

    def test_non_owner_cannot_deactivate_other_sessions(self):
        login(self.client, self.other)

        response = self.client.post(reverse("deactivate_other_sessions", args=[self.user.slug]))

        self.assertEqual(response.status_code, 404)

    def test_deactivate_other_sessions_rejects_get(self):
        login(self.client, self.user)

        response = self.client.get(reverse("deactivate_other_sessions", args=[self.user.slug]))

        self.assertEqual(response.status_code, 405)
