from authlib.integrations.django_oauth2 import AuthorizationServer, ResourceProtector, BearerTokenValidator
from authlib.oauth2.rfc6749 import grants
from authlib.oidc.core import grants as oidc_grants, UserInfo
from django.conf import settings

from authn.models.openid import OAuth2Token, OAuth2AuthorizationCode, OAuth2App

server = AuthorizationServer(OAuth2App, OAuth2Token)

oauth2_token_validator = ResourceProtector()
oauth2_token_validator.register_token_validator(BearerTokenValidator(OAuth2Token))


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def save_authorization_code(self, code, request):
        nonce = request.data.get("nonce")
        client = request.client
        auth_code = OAuth2AuthorizationCode(
            code=code,
            client_id=client.client_id,
            redirect_uri=request.redirect_uri,
            response_type=request.response_type,
            scope=request.scope,
            user=request.user,
            nonce=nonce,
        )
        auth_code.save()
        return auth_code

    def query_authorization_code(self, code, client):
        try:
            item = OAuth2AuthorizationCode.objects.get(code=code, client_id=client.client_id)
        except OAuth2AuthorizationCode.DoesNotExist:
            return None

        if not item.is_expired():
            return item

    def delete_authorization_code(self, authorization_code):
        authorization_code.delete()

    def authenticate_user(self, authorization_code):
        return authorization_code.user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token):
        try:
            item = OAuth2Token.objects.get(refresh_token=refresh_token)
            if item.is_refresh_token_active():
                return item
        except OAuth2Token.DoesNotExist:
            return None

    def authenticate_user(self, credential):
        return credential.user

    def revoke_old_credential(self, credential):
        credential.revoked = True
        credential.save()


class OpenIDCode(oidc_grants.OpenIDCode):
    def exists_nonce(self, nonce, request):
        if nonce is None:
            return False
        try:
            OAuth2AuthorizationCode.objects.get(
                client_id=request.client_id, nonce=nonce
            )
            return True
        except OAuth2AuthorizationCode.DoesNotExist:
            return False

    def get_jwt_config(self, grant):
        return {
            "key": settings.JWT_PRIVATE_KEY,
            "alg": settings.OPENID_JWT_ALGORITHM,
            "iss": settings.APP_HOST,
            "exp": settings.OPENID_JWT_EXPIRE_SECONDS,
        }

    def get_audiences(self, request):
        return [request.client.client_id]

    def generate_user_info(self, user, scope):
        return UserInfo(
            sub=user.slug,
            name=user.full_name,
            email=user.email,
        )


class OpenIDImplicitGrant(OpenIDCode, oidc_grants.OpenIDImplicitGrant):
    pass


server.register_grant(AuthorizationCodeGrant, [OpenIDCode(require_nonce=False)])
server.register_grant(OpenIDImplicitGrant)
server.register_grant(RefreshTokenGrant)
