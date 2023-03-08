import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from django.shortcuts import redirect, render

from authn.models.session import Session
from club import settings
from users.models.user import User

log = logging.getLogger(__name__)

PATH_PREFIXES_WITHOUT_AUTH = [
    "/profile/",
    "/auth/",
    "/intro/",
]


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


def check_user_permissions(request, **context):
    if not request.me:
        return render(request, "auth/access_denied.html", context)

    if any(request.path.startswith(prefix) for prefix in PATH_PREFIXES_WITHOUT_AUTH):
        return None

    if not request.me.is_active_membership:
        log.info("User membership expired. Redirecting to payments page...")
        return redirect("membership_expired")

    if request.me.is_banned:
        log.info("User was banned. Redirecting to 'banned' page...")
        return redirect("banned")

    if request.me.moderation_status == User.MODERATION_STATUS_INTRO:
        log.info("New user. Redirecting to intro...")
        return redirect("intro")

    if request.me.moderation_status == User.MODERATION_STATUS_REJECTED:
        log.info("Rejected user. Redirecting to 'rejected' page...")
        return redirect("rejected")

    if request.me.moderation_status == User.MODERATION_STATUS_ON_REVIEW:
        log.info("User on review. Redirecting to 'on_review' page...")
        return redirect("on_review")

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
