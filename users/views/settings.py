from datetime import datetime, timedelta

import stripe
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render
from django_q.tasks import async_task

from authn.decorators.auth import require_auth
from gdpr.archive import generate_data_archive
from gdpr.models import DataRequests
from search.models import SearchIndex
from users.forms.profile import ProfileEditForm, NotificationsEditForm
from users.models.geo import Geo
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
            Geo.update_for_user(user, fuzzy=True)
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
