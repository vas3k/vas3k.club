from datetime import timedelta, datetime
from uuid import uuid4

from authlib.oauth2.rfc6749 import ClientMixin, scope_to_list, list_to_scope, TokenMixin
from authlib.oidc.core import AuthorizationCodeMixin
from django.conf import settings
from django.db import models
from slugify import slugify

from users.models.user import User
from utils.strings import random_string


class OAuth2App(models.Model, ClientMixin):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    name = models.CharField(max_length=64, unique=True)
    description = models.CharField(max_length=512, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    owner = models.ForeignKey(User, related_name="oauth_apps", null=True, on_delete=models.CASCADE)

    client_id = models.CharField(max_length=32, default="", blank=True, unique=True)
    client_secret = models.CharField(max_length=64, null=True, blank=True)
    service_token = models.CharField(max_length=128, unique=True, db_index=True, null=True, blank=True)

    redirect_uris = models.TextField(default="", max_length=2048)
    scope = models.TextField(default="openid", max_length=256)
    response_type = models.TextField(default="code", max_length=256)
    grant_type = models.TextField(default="authorization_code", max_length=128)
    token_endpoint_auth_method = models.CharField(max_length=120, default="client_secret_basic")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "oauth_apps"

    def save(self, *args, **kwargs):
        if not self.client_id:
            self.client_id = slugify(self.name[:16].lower(), separator="_")

        if not self.client_secret:
            self.client_secret = random_string(length=48)

        if not self.service_token:
            self.service_token = "st_" + random_string(length=48)

        return super().save(*args, **kwargs)

    def get_client_id(self):
        return self.id

    def get_default_redirect_uri(self):
        if self.redirect_uris:
            return [uri.strip() for uri in self.redirect_uris.split(",")]
        return []

    def get_allowed_scope(self, scope):
        if not scope:
            return ""
        allowed = set(scope_to_list(self.scope))
        return list_to_scope([s for s in scope.split() if s in allowed])

    def check_redirect_uri(self, redirect_uri):
        return redirect_uri in self.redirect_uris

    def check_client_secret(self, client_secret):
        return self.client_secret == client_secret

    def check_endpoint_auth_method(self, method, endpoint):
        if endpoint == "token":
            return self.token_endpoint_auth_method == method
        return True

    def check_response_type(self, response_type):
        allowed = self.response_type.split()
        return response_type in allowed

    def check_grant_type(self, grant_type):
        allowed = self.grant_type.split()
        return grant_type in allowed


class OAuth2Token(models.Model, TokenMixin):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    client_id = models.CharField(max_length=32, db_index=True)
    token_type = models.CharField(max_length=40)
    access_token = models.CharField(max_length=255, unique=True, db_index=True, null=False)
    refresh_token = models.CharField(max_length=255, db_index=True)

    scope = models.TextField(default='')
    revoked = models.BooleanField(default=False)
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_in = models.IntegerField(null=False, default=0)

    class Meta:
        db_table = "oauth_tokens"

    def check_client(self, client):
        return self.client_id == client.client_id

    def is_expired(self):
        return self.issued_at + timedelta(seconds=settings.OPENID_JWT_EXPIRE_SECONDS) < datetime.utcnow()

    def is_revoked(self):
        return self.revoked

    def get_client_id(self):
        return str(self.client_id)

    def get_scope(self):
        return self.scope

    def get_expires_in(self):
        return self.expires_in

    def get_expires_at(self):
        return int(self.issued_at.timestamp()) + self.expires_in


class OAuth2AuthorizationCode(models.Model, AuthorizationCodeMixin):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    client_id = models.CharField(max_length=32, db_index=True)
    code = models.CharField(max_length=120, unique=True, null=False)
    redirect_uri = models.TextField(default="", null=True)
    response_type = models.TextField(default="code")
    scope = models.TextField(default="openid", null=True)
    auth_time = models.DateTimeField(auto_now_add=True, db_index=True)
    nonce = models.CharField(max_length=120, default="", null=True)

    class Meta:
        db_table = "oauth_codes"

    def is_expired(self):
        return self.auth_time + timedelta(seconds=settings.OPENID_CODE_EXPIRE_SECONDS) < datetime.utcnow()

    def get_redirect_uri(self):
        return self.redirect_uri

    def get_scope(self):
        return self.scope or ""

    def get_nonce(self):
        return self.nonce if self.nonce else None

    def get_auth_time(self):
        return self.auth_time.timestamp()
