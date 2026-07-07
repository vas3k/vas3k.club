from unittest.mock import patch

import stripe
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from club.exceptions import BadRequest
from tickets.views import deactivate_payment_link, stripe_ticket_sale_webhook


class TestTicketHelpers(TestCase):
    @patch("tickets.views.stripe.PaymentLink.modify")
    def test_deactivate_payment_link_calls_stripe_api(self, mock_modify):
        result = deactivate_payment_link("plink_123")

        self.assertTrue(result)
        mock_modify.assert_called_once_with(
            "plink_123",
            active=False,
            api_key=None,
        )

    @patch("tickets.views.stripe.PaymentLink.modify", side_effect=stripe.error.APIError("boom"))
    def test_deactivate_payment_link_returns_false_on_stripe_error(self, _mock_modify):
        result = deactivate_payment_link("plink_123")
        self.assertFalse(result)


class TestTicketWebhook(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.post("/monies/stripe/webhook_tickets/")

    @patch("tickets.views.parse_stripe_webhook_event")
    def test_webhook_returns_unknown_event_for_unhandled_type(self, mock_parse_event):
        mock_parse_event.return_value = {"type": "customer.updated", "data": {"object": {}}}

        response: HttpResponse = stripe_ticket_sale_webhook(self.request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), "[unknown event]")

    @patch("tickets.views.parse_stripe_webhook_event")
    def test_webhook_returns_bad_request_from_parser(self, mock_parse_event):
        mock_parse_event.side_effect = BadRequest(code=400, message="[invalid payload]")

        response: HttpResponse = stripe_ticket_sale_webhook(self.request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content.decode(), "[invalid payload]")
