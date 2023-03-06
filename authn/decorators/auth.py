import functools

from django.shortcuts import redirect

from authn.helpers import check_user_permissions
from club.exceptions import AccessDenied


def require_auth(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        access_denied = check_user_permissions(request)
        if access_denied:
            return access_denied

        return view(request, *args, **kwargs)

    return wrapper


def require_moderator_role(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.me:
            return redirect("login")

        if not request.me.is_moderator:
            raise AccessDenied()

        return view(request, *args, **kwargs)

    return wrapper


def require_curator_role(view):
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.me:
            return redirect("login")

        if not request.me.is_curator:
            raise AccessDenied()

        return view(request, *args, **kwargs)

    return wrapper
