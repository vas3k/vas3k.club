from datetime import datetime, timedelta

import stripe
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_http_methods
from django_q.tasks import async_task

from authn.cache import clear_auth_token_cache
from authn.decorators.auth import require_auth
from authn.models.session import Session
from common.request import browser_from_useragent
from gdpr.archive import generate_data_archive
from gdpr.models import DataRequests
from search.models import SearchIndex
from users.forms.profile import ProfileEditForm, NotificationsEditForm
from users.models.user import User
from utils.strings import random_hash


@require_auth
def profile_settings(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("profile_settings", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    return render(request, "users/edit/index.html", {"user": user})


@require_auth
def edit_profile(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("edit_profile", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()

            SearchIndex.update_user_index(user)
    else:
        form = ProfileEditForm(instance=user)

    return render(request, "users/edit/profile.html", {"form": form, "user": user})


@require_auth
def edit_account(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("edit_account", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    if request.method == "POST" and request.POST.get("regenerate"):
        user.secret_hash = random_hash(length=16)
        user.save()
        return redirect("edit_account", user.slug, permanent=False)

    return render(request, "users/edit/account.html", {"user": user})


@require_auth
def edit_notifications(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("edit_notifications", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    if request.method == "POST":
        form = NotificationsEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            return redirect("profile", user.slug)
    else:
        form = NotificationsEditForm(instance=user)

    return render(request, "users/edit/notifications.html", {"form": form, "user": user})


@require_auth
def edit_payments(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("edit_payments", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    top_users = User.objects\
        .filter(
            moderation_status=User.MODERATION_STATUS_APPROVED,
            membership_expires_at__gte=datetime.utcnow() + timedelta(days=70)
        )\
        .order_by("-membership_expires_at")[:64]

    subscriptions = []
    if user.stripe_id:
        try:
            stripe_subscriptions = stripe.Subscription.list(customer=user.stripe_id, limit=100)
            subscriptions = [dict(
                id=s["id"],
                next_charge_at=datetime.utcfromtimestamp(s["current_period_end"]),
                amount=int(s["plan"]["amount"] / 100),
                interval=s["plan"]["interval"],
            ) for s in stripe_subscriptions["data"]]
        except (stripe.error.InvalidRequestError, stripe.error.AuthenticationError):
            subscriptions = []

    return render(request, "users/edit/payments.html", {
        "user": user,
        "subscriptions": subscriptions,
        "top_users": top_users,
    })


@require_auth
def edit_bot(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("edit_bot", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    return render(request, "users/edit/bot.html", {"user": user})


@require_auth
def edit_data(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("edit_data", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_god:
        raise Http404()

    return render(request, "users/edit/data.html", {"user": user})


@require_auth
def request_data(request, user_slug):
    if request.method != "POST":
        return redirect("edit_data", user_slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_god:
        raise Http404()

    DataRequests.register_archive_request(user)

    if settings.DEBUG:
        generate_data_archive(user)
    else:
        async_task(generate_data_archive, user=user)

    return render(request, "users/messages/data_requested.html")


@require_auth
def edit_sessions(request, user_slug):
    if user_slug == "me" and request.me:
        return redirect("edit_sessions", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    sessions = list(Session.objects.filter(user=user).order_by("-created_at"))
    current_token = request.my_session.token if request.my_session else None
    for session in sessions:
        session.is_current = session.token == current_token
        session.browser = browser_from_useragent(session.useragent)

    return render(request, "users/edit/sessions.html", {
        "user": user,
        "sessions": sessions,
    })


@require_auth
@require_http_methods(["POST"])
def deactivate_session(request, user_slug, session_id):
    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    session = get_object_or_404(Session, id=session_id, user=user)
    is_current = request.my_session and session.token == request.my_session.token
    token = session.token
    session.delete()
    clear_auth_token_cache(token)

    if is_current:
        return redirect("index")
    return redirect("edit_sessions", user.slug)


@require_auth
@require_http_methods(["POST"])
def deactivate_other_sessions(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    current_token = request.my_session.token if request.my_session else None
    sessions = Session.objects.filter(user=user)
    if current_token:
        sessions = sessions.exclude(token=current_token)

    tokens = list(sessions.values_list("token", flat=True))
    sessions.delete()
    for token in tokens:
        clear_auth_token_cache(token)

    return redirect("edit_sessions", user.slug)
