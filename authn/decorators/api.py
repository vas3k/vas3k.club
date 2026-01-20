import functools
from typing import Optional

from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from django.http import JsonResponse, HttpResponse

from authn.models.openid import OAuth2App, OAuth2Token
from authn.providers.openid import oauth2_token_validator
from club.exceptions import ApiException, ClubException, ApiAuthRequired


def api(require_auth=True, scopes=None):
    def decorator(view):
        @functools.wraps(view)
        def wrapper(request, *args, **kwargs):
            request.oauth_token = None

            # check auth if needed
            if require_auth:
                # requests on behalf of apps (user == owner, for simplicity)
                service_token = request.headers.get("X-Service-Token") or request.GET.get("service_token")
                if service_token:
                    app = app_by_service_token(service_token)
                    if not app:
                        raise ApiAuthRequired("App with this service token not found")

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

                # this user can also come from other types of auth (e.g. cookies)
                if not request.me:
                    raise ApiAuthRequired()

            # execute view and catch exceptions
            status_code = 200
            try:
                results = view(request, *args, **kwargs)
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
                raise ApiException(
                    code=ex.__class__.__name__,
                    title=str(ex),
                )

            # return results in expected format
            if is_ajax(request):  # legacy, change to Content-Type check
                return JsonResponse(data=results, status=status_code, json_dumps_params=dict(ensure_ascii=False))
            elif isinstance(results, dict):
                return JsonResponse(data=results, status=status_code, json_dumps_params=dict(ensure_ascii=False))
            elif isinstance(results, str):
                return HttpResponse(results, content_type="text/plain; charset=utf-8")
            else:
                return results

        return wrapper
    return decorator


def is_ajax(request):
    return bool(request.GET.get("is_ajax"))


def app_by_service_token(service_token) -> Optional[OAuth2App]:
    return OAuth2App.objects\
        .filter(service_token=service_token)\
        .select_related("owner")\
        .first()
