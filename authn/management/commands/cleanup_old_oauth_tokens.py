import logging
from datetime import datetime, timedelta

from django.core.management import BaseCommand

from authn.models.openid import OAuth2AuthorizationCode, OAuth2Token

log = logging.getLogger(__name__)

OAUTH_CODE_CLEANUP_TIMEDELTA = timedelta(hours=1)  # usually it's 5 minutes but we add some delta
OAUTH_TOKENS_CLEANUP_TIMEDELTA = timedelta(days=120)  # because people can still use their "refresh_tokens"


class Command(BaseCommand):
    help = "Cleanup expired oauth tokens and codes"

    def handle(self, *args, **options):
        self.stdout.write("Cleaning up OAuth codes...")
        OAuth2AuthorizationCode.objects.filter(
            auth_time__lt=datetime.utcnow() - OAUTH_CODE_CLEANUP_TIMEDELTA
        ).delete()

        self.stdout.write("Cleaning up expired OAuth tokens...")
        OAuth2Token.objects.filter(
            issued_at__lt=datetime.utcnow() - OAUTH_TOKENS_CLEANUP_TIMEDELTA
        ).delete()

        self.stdout.write("Done 🥙")
