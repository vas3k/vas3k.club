from django.http import JsonResponse
from django.shortcuts import render

from authn.helpers import authorized_user_with_session
from club.exceptions import ClubException, ApiException


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
            return render(request, "error.html", {
                "code": exception.code,
                "title": exception.title,
                "message": exception.message,
                "data": exception.data,
            }, status=400)
