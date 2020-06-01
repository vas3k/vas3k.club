from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.shortcuts import redirect
from django.urls import reverse

from auth.helpers import auth_required
from auth.models import Session
from club.exceptions import AccessDenied
from posts.models import Post
from users.models.user import User
from utils.strings import random_string


def login(request):
    if request.me:
        return redirect("profile", request.me.slug)

    goto = request.GET.get("goto")

    # TODO: for now we have only Patreon login, let's redirect user there immediately
    if goto:
        return redirect(reverse("patreon_login") + f"?goto={goto}")
    else:
        return redirect("patreon_login")

    # TODO: use it in future
    # return render(request, "auth/login.html")


@auth_required
def logout(request):
    token = request.COOKIES.get("token")
    Session.objects.filter(token=token).delete()
    cache.delete(f"token:{token}:session")
    return redirect("index")


def debug_dev_login(request):
    if not settings.DEBUG:
        raise AccessDenied(title="Эта фича доступна только при DEBUG=true")

    user, is_created = User.objects.get_or_create(
        slug="dev",
        defaults=dict(
            membership_platform_type=User.MEMBERSHIP_PLATFORM_PATREON,
            membership_platform_id="DUMMY",
            email="dev@dev.dev",
            full_name="Senior 23 y.o. Developer",
            company="FAANG",
            position="Team Lead конечно",
            balance=10000,
            membership_started_at=datetime.utcnow(),
            membership_expires_at=datetime.utcnow() + timedelta(days=365 * 100),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_email_verified=True,
            is_profile_complete=True,
            is_profile_reviewed=True,
            is_profile_rejected=False,
            roles=["god"],
        ),
    )

    if is_created:
        Post.upsert_user_intro(user, "Очень плохое интро", is_visible=True)

    session = Session.objects.create(
        user=user,
        token=random_string(length=32),
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=365 * 100),
    )

    response = redirect("profile", user.slug)
    response.set_cookie(
        key="token",
        value=session.token,
        max_age=settings.SESSION_COOKIE_AGE,
        httponly=True,
        secure=False,
    )
    return response
