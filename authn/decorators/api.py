import functools
import logging
from types import SimpleNamespace
from typing import Any, Callable

from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse

from authn.models.openid import OAuth2App, OAuth2Token
from authn.providers.openid import oauth2_token_validator
from authn.helpers import get_access_denied_reason
from club.exceptions import ApiAccessDenied, ApiException, ClubException, ApiAuthRequired

log = logging.getLogger(__name__)


def api(require_auth: bool = True) -> Callable:
    def decorator(view: Callable) -> Callable:
        @functools.wraps(view)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            request.oauth_token = None

            if require_auth:
                _authenticate_api_request(request)
                if not request.me:
                    raise ApiAuthRequired()
                reason = get_access_denied_reason(request.me)
                if reason:
                    raise ApiAccessDenied(code=reason)

            try:
                result = view(request, *args, **kwargs)
            except ApiException:
                raise
            except Http404:
                raise ApiException(code="not-found", title="Not found")
            except ClubException as ex:
                raise ApiException(
                    code=ex.code,
                    title=ex.title,
                    message=ex.message,
                    data=ex.data,
                )

            return _serialize_api_response(result)

        return wrapper
    return decorator

def _authenticate_api_request(request: HttpRequest) -> None:
    service_token: str | None = request.headers.get("X-Service-Token") or request.GET.get("service_token")
    if service_token:
        if request.GET.get("service_token"):
            log.warning("service_token passed as GET parameter, use X-Service-Token header instead")

        app: OAuth2App | None = OAuth2App.by_service_token(service_token)
        if not app:
            raise ApiAuthRequired("App with this service token not found")

        request.me = app.owner

        scope: str = app.scope or ""
        request.oauth_token = SimpleNamespace(
            user=request.me,
            client_id=app.client_id,
            token_type="Service",
            access_token=service_token,
            scope=scope,
            get_scopes=lambda: OAuth2Token.parse_scope(scope),
        )
        return

    auth_header: str | None = request.headers.get("Authorization")
    if auth_header:
        try:
            token = oauth2_token_validator.acquire_token(request, None)
        except MissingAuthorizationError as ex:
            raise ApiAuthRequired(title="Missing OAuth token", message=str(ex))
        except OAuth2Error as ex:
            raise ApiAuthRequired(title="OAuth token error", message=str(ex))

        request.me = token.user
        request.oauth_token = token

def _serialize_api_response(result: Any) -> HttpResponse:
    if isinstance(result, dict):
        return JsonResponse(data=result, json_dumps_params={"ensure_ascii": False})
    elif isinstance(result, str):
        return HttpResponse(result, content_type="text/plain; charset=utf-8")
    else:
        return result
