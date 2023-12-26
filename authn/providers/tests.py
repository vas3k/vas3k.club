from datetime import datetime, timedelta

import django
from django.test import SimpleTestCase

django.setup()  # todo: how to run tests from PyCharm without this workaround?

from authn.providers.common import Membership
from authn.providers.patreon import parse_active_membership


class UnitTestsParseActiveMembership(SimpleTestCase):
    def setUp(self):
        self.stub_patreon_response_oauth_identity = {
            "data": {
                "attributes": {
                    "about": "A Patreon Platform User",
                    "created": "2018-04-01T00:36:26+00:00",
                    "email": "user-email@email.com",
                    "first_name": "Firstname",
                    "full_name": "FullName With Space",
                    "image_url": "https://url.example",
                    "last_name": "Lastname",
                    "social_connections": {
                        "deviantart": None,
                        "discord": None,
                        "facebook": None,
                        "reddit": None,
                        "spotify": None,
                        "twitch": None,
                        "twitter": {
                            "user_id": "12345"
                        },
                        "youtube": None
                    },
                    "thumb_url": "https://url.example",
                    "url": "https://www.patreon.com/example",
                    "vanity": "platform"
                },
                "id": "12345689",
                "type": "user"
            },
            "included": [
                {
                    "attributes": {
                        "full_name": "Member FullName",
                        "email": "member-email@email.com",
                        "is_follower": False,
                        "last_charge_date": "2018-04-01T21:28:06+00:00",
                        "last_charge_status": "Paid",
                        "lifetime_support_cents": 400,
                        "patron_status": "active_patron",
                        "currently_entitled_amount_cents": 100,
                        "pledge_relationship_start": "2018-04-01T16:33:27.861405+00:00",
                        "will_pay_amount_cents": 100
                    },
                    "id": "03ca69c3-ebea-4b9a-8fac-e4a837873254",
                    "type": "member"
                }
            ]
        }

    def test_successful_parsed(self):
        result: Membership = parse_active_membership(self.stub_patreon_response_oauth_identity)

        self.assertIsNotNone(result)
        self.assertTrue(isinstance(result, Membership))

        self.assertEqual(result.platform, "patreon")
        self.assertEqual(result.user_id, "12345689")
        self.assertEqual(result.full_name, "FullName With Space")
        self.assertEqual(result.email, "user-email@email.com")
        self.assertEqual(result.image, None)
        self.assertEqual(result.started_at, datetime(2018, 4, 1, 0, 0))
        self.assertEqual(result.expires_at, datetime(2018, 5, 16, 0, 0))
        self.assertEqual(result.lifetime_support_cents, 400)
        self.assertEqual(result.currently_entitled_amount_cents, 100)

    def test_wrong_data(self):
        result = parse_active_membership({})
        self.assertIsNone(result)

        result = parse_active_membership({"data": {}})  # no included
        self.assertIsNone(result)

        result = parse_active_membership({"included": {}})  # no data
        self.assertIsNone(result)
