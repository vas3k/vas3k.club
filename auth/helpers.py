import logging
from datetime import datetime

from django.shortcuts import redirect, render

from auth.models import Session
from club.exceptions import AccessDenied

log = logging.getLogger(__name__)


def authorized_user_with_session(request):
    token = request.COOKIES.get("token") or request.GET.get("token")
    if not token:
        return None, None

    # TODO: don't cache it with user profile
    # session = cache.get(f"token:{token}:session")
    # if not session:
    session = Session.objects\
        .filter(token=token)\
        .order_by()\
        .select_related("user")\
        .first()
        # cache.set(f"token:{token}:session", session, timeout=60 * 60)

    if not session or session.expires_at <= datetime.utcnow():
        log.info("User session has expired")
        return None, None  # session is expired

    return session.user, session


def authorized_user(request):
    user, _ = authorized_user_with_session(request)
    return user


def auth_required(view):
    def wrapper(request, *args, **kwargs):
        access_denied = check_user_permissions(request)
        if access_denied:
            return access_denied

        return view(request, *args, **kwargs)

    return wrapper


def check_user_permissions(request, **context):
    if not request.me:
        return render(request, "auth/access_denied.html", context)

    # FIXME: really bad IF, fix it
    if not request.path.startswith("/profile/") \
            and not request.path.startswith("/auth/") \
            and not request.path.startswith("/intro/") \
            and not request.path.startswith("/telegram/"):

        if request.me.membership_expires_at < datetime.utcnow():
            log.info("User membership expired. Redirecting")
            return redirect("membership_expired")

        if request.me.is_banned:
            log.info("User banned. Redirecting")
            return redirect("banned")

        if not request.me.is_profile_complete:
            log.info("User profile is not completed. Redirecting")
            return redirect("intro")

        if request.me.is_profile_rejected:
            log.info("User rejected. Redirecting")
            return redirect("rejected")

        if not request.me.is_profile_reviewed:
            log.info("User on review. Redirecting")
            return redirect("on_review")

    return None


def moderator_role_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.me:
            return redirect("login")

        if not request.me.is_moderator:
            raise AccessDenied()

        return view(request, *args, **kwargs)

    return wrapper


def auth_switch(no, yes):
    def result(request, *args, **kwargs):
        is_authorized = request.me is not None
        if is_authorized:
            return yes(request, *args, **kwargs)
        else:
            return no(request, *args, **kwargs)

    return result
