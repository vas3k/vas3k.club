from django.http import JsonResponse
from django.shortcuts import render

from authn.helpers import authorized_user_with_session
from club.exceptions import ClubException, ApiException
from club.rendering import wants_json
from club.serializers import serialize


def json_suffix(get_response):
    """Strip .json suffix from URL path and flag request for JSON response.

    Runs AFTER URL routing fails for .json paths. If the original path
    ends with .json and gets a 404, retries without the suffix.
    Existing explicit .json routes (like /feed.json, /user/slug.json)
    are matched normally and never hit this retry logic.
    """
    def middleware(request):
        response = get_response(request)
        if response.status_code == 404 and request.path_info.endswith(".json"):
            original_path = request.path_info
            request.path_info = original_path[:-5] or "/"
            request.GET = request.GET.copy()
            request.GET["format"] = "json"
            response = get_response(request)
            request.path_info = original_path
        return response

    return middleware


def me(get_response):
    def middleware(request):
        request.me, request.my_session = authorized_user_with_session(request)

        response = get_response(request)

        return response

    return middleware


class ExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, ApiException):
            return JsonResponse({
                "error": {
                    "code": exception.code,
                    "title": exception.title,
                    "message": exception.message,
                    "data": exception.data,
                }
            }, status=400)

        if isinstance(exception, ClubException):
            if wants_json(request):
                return JsonResponse({
                    "error": {
                        "code": exception.code,
                        "title": exception.title,
                        "message": exception.message,
                        "data": exception.data,
                    }
                }, status=400)

            return render(request, "error.html", {
                "code": exception.code,
                "title": exception.title,
                "message": exception.message,
                "data": exception.data,
            }, status=400)


class JsonApiMiddleware:
    """Intercepts TemplateResponse and returns JSON when the client requests it.

    Triggered by Accept: application/json header or ?format=json query param.
    Only works with views that return TemplateResponse (via club.rendering.render).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_template_response(self, request, response):
        if not wants_json(request):
            return response

        if not hasattr(response, "context_data") or response.context_data is None:
            return response

        # Replace the TemplateResponse's rendering with JSON serialization.
        # Django calls response.render() after process_template_response,
        # so we override the template rendering to produce JSON instead.
        original_context = response.context_data

        def render_json():
            data = serialize(original_context)
            json_response = JsonResponse(data, json_dumps_params=dict(ensure_ascii=False))
            response.content = json_response.content
            response["Content-Type"] = json_response["Content-Type"]
            return response

        response.render = render_json
        return response
