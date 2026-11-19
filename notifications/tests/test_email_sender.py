from unittest.mock import patch

from django.test import SimpleTestCase

from notifications.email.sender import send_transactional_email, send_mass_email


class EmailRecipientTests(SimpleTestCase):
    def test_invalid_recipient_is_skipped_before_rendering_or_smtp(self):
        for send in (send_transactional_email, send_mass_email):
            with self.subTest(send=send.__name__), patch("notifications.email.sender.prepare_letter") as prepare, patch(
                "notifications.email.sender.EmailMultiAlternatives",
            ) as email:
                self.assertEqual(send("a@b.com'", "subject", "body", "https://example.com/unsubscribe"), 0)
                prepare.assert_not_called()
                email.assert_not_called()

    def test_valid_apostrophe_in_local_part_is_preserved(self):
        for send in (send_transactional_email, send_mass_email):
            with self.subTest(send=send.__name__), patch(
                "notifications.email.sender.prepare_letter", return_value="body",
            ), patch("notifications.email.sender.EmailMultiAlternatives") as email:
                send("o'brien@example.com", "subject", "body", "https://example.com/unsubscribe")
                self.assertEqual(email.call_args.kwargs["to"], ["o'brien@example.com"])
                email.return_value.send.assert_called_once()
