import logging

from authlib.integrations.django_oauth2 import RevocationEndpoint
from authlib.jose import JsonWebKey
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import InvalidClientError, UnsupportedResponseTypeError, UnsupportedGrantTypeError, \
    InvalidScopeError
from django.conf import settings
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from authn.decorators.auth import require_auth
from authn.providers.openid import server
from authn.decorators.api import api

log = logging.getLogger(__name__)


@require_auth
def openid_authorize(request):
    if request.method == "GET":
        try:
            grant = server.get_consent_grant(request, end_user=request.me)
        except InvalidClientError:
            return render(request, "error.html", {
                "title": f"Приложение '{request.GET.get('client_id')}' не найдено",
                "message": "Убедитесь, что правильно указали client_id или обратитесь к автору приложения"
            })
        except (UnsupportedResponseTypeError, UnsupportedGrantTypeError, InvalidScopeError):
            return render(request, "error.html", {
                "title": f"Неправильные параметры запроса OAuth",
                "message": "Параметры response_type, grant, scope где-то потерялись или не поддерживаются"
            })
        except OAuth2Error as ex:
            return render(request, "error.html", {
                "title": "Ошибка OAuth",
                "message": str(ex)
            })

        client = grant.client
        scope = client.get_allowed_scope(grant.request.scope)

        return render(request, "openid/authorize.html", {
            "app": client,
            "user": request.me,
            "grant": grant,
            "scope": scope,
        })

    if request.POST.get("confirmed"):
        # granted by resource owner
        return server.create_authorization_response(request, grant_user=request.me)

    # denied by resource owner
    return server.create_authorization_response(request, grant_user=None)


@require_http_methods(["POST"])
def openid_issue_token(request):
    return server.create_token_response(request)


@require_http_methods(["POST"])
def openid_revoke_token(request):
    return server.create_endpoint_response(RevocationEndpoint.ENDPOINT_NAME, request)


server.register_endpoint(RevocationEndpoint)


@api(require_auth=False)
def openid_well_known_configuration(request):
    return {
        "issuer": settings.APP_HOST,
        "authorization_endpoint": f"{settings.APP_HOST}{reverse('openid_authorize')}",
        "token_endpoint": f"{settings.APP_HOST}{reverse('openid_issue_token')}",
        "token_endpoint_auth_methods_supported": ["client_secret_basic"],
        "token_endpoint_auth_signing_alg_values_supported": ["RS512", "RS256", "ES256"],
        "userinfo_endpoint": f"{settings.APP_HOST}/user/me.json",
        "jwks_uri": f"{settings.APP_HOST}{reverse('openid_well_known_jwks')}",
        "registration_endpoint": f"{settings.APP_HOST}{reverse('join')}",
        "response_types_supported": ["code", "code id_token", "id_token", "token id_token"],
        "acr_values_supported": [],
        "subject_types_supported": ["public", "pairwise"],
        "userinfo_signing_alg_values_supported": ["RS512", "RS256", "ES256", "HS256"],
        "userinfo_encryption_alg_values_supported": ["RSA1_5", "A128KW"],
        "userinfo_encryption_enc_values_supported": ["A128CBC-HS256", "A128GCM"],
        "id_token_signing_alg_values_supported": ["RS512", "RS256", "ES256", "HS256"],
        "id_token_encryption_alg_values_supported": ["RSA1_5", "A128KW"],
        "id_token_encryption_enc_values_supported": ["A128CBC-HS256", "A128GCM"],
        "request_object_signing_alg_values_supported": ["RS512", "RS256", "ES256"],
        "claims_supported": ["sub", "iss", "auth_time", "acr", "name", "email"],
        "claims_parameter_supported": True,
        "ui_locales_supported": ["en-US", "ru-RU"]
    }


@api(require_auth=False)
def openid_well_known_jwks(request):
    openid_jwk = JsonWebKey.import_key(raw=settings.JWT_PUBLIC_KEY)
    return {
        "keys": [
            {
                "use": "sig",
                "alg": settings.OPENID_JWT_ALGORITHM,
                **openid_jwk.tokens
            },
        ]
    }
