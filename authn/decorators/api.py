import functools
import logging
from typing import Optional

from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from django.http import Http404, JsonResponse
from django.http.response import HttpResponseBase

from authn.models.openid import OAuth2App, OAuth2Token
from authn.providers.openid import oauth2_token_validator
from authn.helpers import get_access_denied_reason
from club.exceptions import ApiAccessDenied, ApiException, ClubException, ApiAuthRequired, ApiNotFound


log = logging.getLogger(__name__)


def api(require_auth=True, scopes=None):
    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            request.oauth_token = None

            # try to resolve auth (always, even if not required)
            # requests on behalf of apps (user == owner, for simplicity)
            service_token = request.headers.get("X-Service-Token") or request.GET.get("service_token")
            if service_token:
                app = app_by_service_token(service_token)
                if not app:
                    raise ApiAuthRequired(title="App with this service token not found")

                request.me = app.owner

                # create "fake" token so we always have "request.oauth_token" set
                request.oauth_token = OAuth2Token(
                    user=request.me,
                    client_id=app.client_id,
                    token_type="Service",
                    access_token=service_token,
                    refresh_token=service_token,
                    scope=app.scope,
                )

            # oauth requests with Bearer token
            oauth_access_token = request.headers.get("Authorization")
            if oauth_access_token:
                try:
                    token = oauth2_token_validator.acquire_token(request, scopes)
                except MissingAuthorizationError as ex:
                    raise ApiAuthRequired(title="Missing OAuth token", message=str(ex))
                except OAuth2Error as ex:
                    raise ApiAuthRequired(title="OAuth token error", message=str(ex))

                request.me = token.user
                request.oauth_token = token

            # require auth if needed
            if require_auth:
                # this user can also come from other types of auth (e.g. cookies)
                if not request.me:
                    raise ApiAuthRequired()

                reason = get_access_denied_reason(request.me)
                if reason:
                    raise ApiAccessDenied(code=reason)

            # execute view and catch exceptions
            try:
                results = view(request, *args, **kwargs)
            except Http404 as ex:
                raise ApiNotFound() from ex
            except ApiException:
                raise  # simply re-raise
            except ClubException as ex:
                # wrap and re-raise
                raise ApiException(
                    code=ex.code,
                    title=ex.title,
                    message=ex.message,
                    data=ex.data,
                )
            except Exception as ex:
                log.exception("Unhandled exception in API view %s", view.__name__)
                raise ApiException(code=ex.__class__.__name__) from ex

            if isinstance(results, HttpResponseBase):
                return results

            return JsonResponse(results, json_dumps_params={"ensure_ascii": False})

        return wrapper
    return decorator


def app_by_service_token(service_token) -> Optional[OAuth2App]:
    return OAuth2App.objects\
        .filter(service_token=service_token)\
        .select_related("owner")\
        .first()
