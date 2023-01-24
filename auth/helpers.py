import logging
import random
from datetime import datetime, timedelta

import jwt
from django.shortcuts import redirect, render, get_object_or_404

from auth.models import Session, Apps
from club import settings
from club.exceptions import AccessDenied, ApiAuthRequired, ClubException, ApiException
from users.models.user import User
from utils.strings import random_string

log = logging.getLogger(__name__)

PATH_PREFIXES_WITHOUT_AUTH = [
    "/profile/",
    "/auth/",
    "/intro/",
]


def authorized_user(request):
    user, _ = authorized_user_with_session(request)
    return user


def authorized_user_with_session(request):
    # normal user access
    auth_token = request.COOKIES.get("token") or request.GET.get("token")
    if auth_token:
        return user_by_token(auth_token)

    # oauth requests for API
    jwt_token = request.COOKIES.get("jwt") or request.GET.get("jwt")
    if jwt_token:
        return user_by_jwt(jwt_token)

    # requests on behalf of apps (user == owner, just for simplicity)
    service_token = request.GET.get("service_token")
    if service_token:
        return user_by_service_token(service_token)

    return None, None


def user_by_token(token):
    session = Session.objects\
        .filter(token=token)\
        .order_by()\
        .select_related("user")\
        .first()

    if not session or session.expires_at <= datetime.utcnow():
        return None, None  # session is expired

    return session.user, session


def user_by_service_token(service_token):
    app = Apps.objects\
        .filter(service_token=service_token)\
        .select_related("owner")\
        .first()

    if not app:
        return None, None  # no such app

    return app.owner, None


def user_by_jwt(jwt_token):
    try:
        payload = jwt.decode(jwt_token, settings.JWT_PUBLIC_KEY, algorithms=[settings.JWT_ALGORITHM])
    except (jwt.DecodeError, jwt.ExpiredSignatureError):
        return None, None  # bad jwt token

    user = get_object_or_404(User, slug=payload["user_slug"])

    return user, None


def auth_required(view):
    def wrapper(request, *args, **kwargs):
        access_denied = check_user_permissions(request)
        if access_denied:
            return access_denied

        return view(request, *args, **kwargs)

    return wrapper


def check_user_permissions(request, **context):
    if any(request.path.startswith(prefix) for prefix in PATH_PREFIXES_WITHOUT_AUTH):
        return None

    if not request.me:
        return render(request, "auth/access_denied.html", context)

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


def moderator_role_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.me:
            return redirect("login")

        if not request.me.is_moderator:
            raise AccessDenied()

        return view(request, *args, **kwargs)

    return wrapper


def curator_role_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.me:
            return redirect("login")

        if not request.me.is_curator:
            raise AccessDenied()

        return view(request, *args, **kwargs)

    return wrapper


def api_required(view):
    def wrapper(request, *args, **kwargs):
        if not request.me:
            raise ApiAuthRequired()

        try:
            return view(request, *args, **kwargs)
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

    return wrapper


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


def create_fake_user(avatar=None):
    slug = _create_free_user_slug()

    user = User.objects.create(
        slug=slug,
        patreon_id=random_string(),
        membership_platform_type=User.MEMBERSHIP_PLATFORM_PATREON,
        email=slug + "@random.dev",
        full_name="%s %d y.o. Developer" % (random.choice(["Максим", "Олег"]), random.randint(18, 101)),
        avatar=avatar,
        company="Acme Corp.",
        position=random.choice(["Подниматель пингвинов", "Опускатель серверов", "Коллектор пивных бутылок"]),
        balance=10000,
        membership_started_at=datetime.utcnow(),
        membership_expires_at=datetime.utcnow() + timedelta(days=365 * 100),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_email_verified=True,
        moderation_status=User.MODERATION_STATUS_APPROVED,
    )

    return user


def _create_free_user_slug() -> str:
    while True:
        slug = "random_" + random_string()
        if not User.objects.filter(slug=slug).exists():
            return slug
