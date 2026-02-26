import logging
from datetime import datetime, timedelta
from enum import StrEnum, unique
from typing import Optional, Tuple
from urllib.parse import urlparse

from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from django.conf import settings

from authn.models.session import Session
from users.models.user import User

log = logging.getLogger(__name__)

PATH_PREFIXES_WITHOUT_AUTH = [
    "/profile/",
    "/auth/",
    "/intro/",
]


def is_safe_url(url):
    if not url:
        return False
    allowed_host = urlparse(settings.APP_HOST).netloc
    return url_has_allowed_host_and_scheme(url, allowed_hosts={allowed_host})


def authorized_user(request):
    user, _ = authorized_user_with_session(request)
    return user


def authorized_user_with_session(request) -> Tuple[Optional[User], Optional[Session]]:
    auth_token = request.COOKIES.get("token") or request.GET.get("token")
    if auth_token:
        return user_by_token(auth_token)

    return None, None


def user_by_token(token) -> Tuple[Optional[User], Optional[Session]]:
    session = Session.objects\
        .filter(token=token)\
        .order_by()\
        .select_related("user")\
        .first()

    if not session or session.expires_at <= datetime.utcnow():
        return None, None  # session is expired

    return session.user, session


@unique
class AccessDeniedReason(StrEnum):
    BANNED = "banned"
    MEMBERSHIP_EXPIRED = "membership_expired"
    INTRO = "intro"
    REJECTED = "rejected"
    ON_REVIEW = "on_review"


def get_access_denied_reason(user) -> Optional[AccessDeniedReason]:
    if user.is_banned:
        return AccessDeniedReason.BANNED

    if not user.is_active_membership:
        return AccessDeniedReason.MEMBERSHIP_EXPIRED

    if user.moderation_status in (
        User.MODERATION_STATUS_INTRO,
        User.MODERATION_STATUS_REJECTED,
        User.MODERATION_STATUS_ON_REVIEW,
    ):
        return AccessDeniedReason(user.moderation_status)

    return None


def check_user_permissions(request, **context):
    if not request.me:
        return render(request, "auth/access_denied.html", context)

    if any(request.path.startswith(prefix) for prefix in PATH_PREFIXES_WITHOUT_AUTH):
        return None

    reason = get_access_denied_reason(request.me)
    if reason:
        log.info(f"Access denied ({reason}). Redirecting...")
        return redirect(reason)

    return None


def auth_switch(yes, no):
    def result(request, *args, **kwargs):
        is_authorized = request.me is not None
        if is_authorized:
            return yes(request, *args, **kwargs)
        else:
            return no(request, *args, **kwargs)

    return result


def set_session_cookie(response, user, session):
    response.set_cookie(
        key="token",
        value=session.token,
        expires=max(user.membership_expires_at, datetime.utcnow() + timedelta(days=30)),
        httponly=True,
        secure=not settings.DEBUG,
    )
    return response
