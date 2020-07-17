from django.http import JsonResponse
from django.shortcuts import render

from auth.helpers import authorized_user_with_session
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
                    "title": exception.title,
                    "message": exception.message
                }
            }, status=400)

        if isinstance(exception, ClubException):
            return render(
                request,
                "error.html",
                {"title": exception.title, "message": exception.message},
                status=400,
            )
