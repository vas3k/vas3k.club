import logging
from datetime import datetime, timedelta

from django.core.cache import cache
from django.core.management import BaseCommand

from authn.cache import auth_token_cache_key
from authn.models.openid import OAuth2AuthorizationCode, OAuth2Token
from authn.models.session import Code, Session

log = logging.getLogger(__name__)

OAUTH_CODE_CLEANUP_TIMEDELTA = timedelta(hours=1)  # usually it's 5 minutes but we add some delta
OAUTH_TOKENS_CLEANUP_TIMEDELTA = timedelta(days=120)  # because people can still use their "refresh_tokens"


class Command(BaseCommand):
    help = "Cleanup expired sessions, auth codes, and OAuth tokens"

    def handle(self, *args, **options):
        now = datetime.utcnow()

        self.stdout.write("Cleaning up expired sessions...")
        expired_sessions = Session.objects.filter(expires_at__lte=now)
        tokens = list(expired_sessions.values_list("token", flat=True))
        deleted_sessions, _ = expired_sessions.delete()
        if tokens:
            cache.delete_many([auth_token_cache_key(token) for token in tokens])
        self.stdout.write(f"Deleted {deleted_sessions} sessions")

        self.stdout.write("Cleaning up expired auth codes...")
        deleted_codes, _ = Code.objects.filter(expires_at__lte=now).delete()
        self.stdout.write(f"Deleted {deleted_codes} codes")

        self.stdout.write("Cleaning up OAuth codes...")
        OAuth2AuthorizationCode.objects.filter(
            auth_time__lt=now - OAUTH_CODE_CLEANUP_TIMEDELTA
        ).delete()

        self.stdout.write("Cleaning up expired OAuth tokens...")
        OAuth2Token.objects.filter(
            issued_at__lt=now - OAUTH_TOKENS_CLEANUP_TIMEDELTA
        ).delete()

        self.stdout.write("Done 🥙")
