from datetime import datetime, timedelta
from io import StringIO

from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase

from authn.cache import auth_token_cache_key
from authn.models.session import Code, Session
from users.models.user import User


class CleanupOldOauthTokensCommandTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create(
            email="cleanup@xx.com",
            membership_started_at=datetime.now() - timedelta(days=5),
            membership_expires_at=datetime.now() + timedelta(days=5),
        )

    def test_deletes_expired_sessions_and_keeps_active_ones(self):
        expired = Session.create_for_user(self.user)
        expired.expires_at = datetime.utcnow() - timedelta(days=1)
        expired.save()
        active = Session.create_for_user(self.user)

        call_command("cleanup_old_oauth_tokens", stdout=StringIO())

        self.assertFalse(Session.objects.filter(id=expired.id).exists())
        self.assertTrue(Session.objects.filter(id=active.id).exists())

    def test_clears_auth_cache_for_deleted_sessions(self):
        expired = Session.create_for_user(self.user)
        expired.expires_at = datetime.utcnow() - timedelta(days=1)
        expired.save()
        cache_key = auth_token_cache_key(expired.token)
        cache.set(cache_key, ("cached", expired), timeout=60)

        call_command("cleanup_old_oauth_tokens", stdout=StringIO())

        self.assertIsNone(cache.get(cache_key))

    def test_deletes_expired_codes_and_keeps_active_ones(self):
        expired = Code.create_for_user(self.user, recipient="expired@xx.com")
        expired.expires_at = datetime.utcnow() - timedelta(minutes=1)
        expired.save()
        active = Code.create_for_user(self.user, recipient="active@xx.com")

        call_command("cleanup_old_oauth_tokens", stdout=StringIO())

        self.assertFalse(Code.objects.filter(id=expired.id).exists())
        self.assertTrue(Code.objects.filter(id=active.id).exists())
