import logging
from datetime import datetime, timedelta

from django.core.management import BaseCommand

from auth.exceptions import PatreonException
from auth.models import Session
from auth.providers import patreon
from auth.providers.patreon import fetch_user_data
from users.models.user import User


class Command(BaseCommand):
    help = "Fetches expiring accounts and tries to renew the subscription"

    def add_arguments(self, parser):
        parser.add_argument("--days-before", type=int, required=False, default=2)
        parser.add_argument("--days-after", type=int, required=False, default=5)
        parser.add_argument("--email", type=str, required=False)

    def handle(self, *args, **options):
        if options.get("email"):
            self.stdout.write(f"Selecting a user with email: {options['email']}")
            expiring_users = User.objects.filter(email=options["email"])
        else:
            self.stdout.write(f"Selecting users with expired subscriptions "
                              f"between {options['days_before']} days before and {options['days_after']} days after")
            expiring_users = User.objects\
                .filter(
                    membership_platform_type=User.MEMBERSHIP_PLATFORM_PATREON,
                    membership_expires_at__gte=datetime.utcnow() - timedelta(days=options["days_before"]),
                    membership_expires_at__lte=datetime.utcnow() + timedelta(days=options["days_after"]),
                )\
                .all()

        for user in expiring_users:
            self.stdout.write(f"Checking user: {user.slug}")
            if user.membership_platform_type == User.MEMBERSHIP_PLATFORM_PATREON:
                if not user.membership_platform_data or "refresh_token" not in user.membership_platform_data:
                    self.stdout.write(f"No auth data for user: {user.slug}")
                    continue

                # refresh user data id needed
                try:
                    auth_data = patreon.refresh_auth_data(user.membership_platform_data["refresh_token"])
                    user.membership_platform_data = {
                        "access_token": auth_data["access_token"],
                        "refresh_token": auth_data["refresh_token"],
                    }
                except PatreonException as ex:
                    self.stdout.write(f"Can't refresh user data {user.slug}: {ex}. Cleaning up active sessions...")
                    Session.objects.filter(user=user).delete()

                # fetch user pledge status
                try:
                    user_data = fetch_user_data(user.membership_platform_data["access_token"])
                    self.stdout.write(f"Pledge status: {user_data}")
                except PatreonException as ex:
                    self.stdout.write(f"Invalid patreon credentials for user {user.slug}: {ex}")
                    Session.objects.filter(user=user).delete()
                    continue

                # check the new expiration date
                membership = patreon.parse_active_membership(user_data)
                if membership:
                    if membership.expires_at >= user.membership_expires_at:
                        user.membership_expires_at = membership.expires_at
                        user.balance = membership.lifetime_support_cents / 100
                        # TODO: ^^^ remove when the real money comes in
                        self.stdout.write(f"New expiration date for user {user.slug} — {membership.expires_at}")
                else:
                    Session.objects.filter(user=user).delete()

                user.save()
                self.stdout.write(f"User processed: {user.slug}")

            else:
                self.stderr.write(f"No renewing scenario for the platform: {user.membership_platform_type}")

        self.stdout.write("Done 🥙")
