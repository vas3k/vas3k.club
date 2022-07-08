import os
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render, redirect

from auth.helpers import auth_required
from club.exceptions import AccessDenied
from landing.forms import GodmodeNetworkSettingsEditForm, GodmodeDigestEditForm, GodmodeInviteForm
from landing.models import GodSettings
from notifications.email.invites import send_invited_email
from users.models.user import User

EXISTING_DOCS = [
    os.path.splitext(f)[0]  # get only filenames
    for f in os.listdir(os.path.join(settings.BASE_DIR, "frontend/html/docs"))
    if f.endswith(".html")
]


def landing(request):
    stats = cache.get("landing_stats")
    if not stats:
        stats = {
            "users": User.registered_members().count(),
            "countries": User.registered_members().values("country")
            .annotate(total=Count("country")).order_by().count() + 1,
        }
        cache.set("landing_stats", stats, settings.LANDING_CACHE_TIMEOUT)

    return render(request, "landing.html", {
        "stats": stats
    })


def docs(request, doc_slug):
    if doc_slug not in EXISTING_DOCS:
        raise Http404()

    return render(request, f"docs/{doc_slug}.html")


@auth_required
def godmode_settings(request):
    if not request.me.is_god:
        raise AccessDenied()

    return render(request, "admin/godmode.html")


@auth_required
def godmode_network_settings(request):
    if not request.me.is_god:
        raise AccessDenied()

    god_settings = GodSettings.objects.first()

    if request.method == "POST":
        form = GodmodeNetworkSettingsEditForm(request.POST, request.FILES, instance=god_settings)
        if form.is_valid():
            form.save()
            return redirect("godmode_settings")
    else:
        form = GodmodeNetworkSettingsEditForm(instance=god_settings)

    return render(request, "admin/simple_form.html", {"form": form})


@auth_required
def godmode_digest_settings(request):
    if not request.me.is_god:
        raise AccessDenied()

    god_settings = GodSettings.objects.first()

    if request.method == "POST":
        form = GodmodeDigestEditForm(request.POST, request.FILES, instance=god_settings)
        if form.is_valid():
            form.save()
            return redirect("godmode_settings")
    else:
        form = GodmodeDigestEditForm(instance=god_settings)

    return render(request, "admin/simple_form.html", {"form": form})


@auth_required
def godmode_invite(request):
    if not request.me.is_god:
        raise AccessDenied()

    if request.method == "POST":
        form = GodmodeInviteForm(request.POST, request.FILES)
        if form.is_valid():
            email = form.cleaned_data["email"]
            days = form.cleaned_data["days"]
            now = datetime.utcnow()
            user, is_created = User.objects.get_or_create(
                email=email,
                defaults=dict(
                    membership_platform_type=User.MEMBERSHIP_PLATFORM_DIRECT,
                    full_name=email[:email.find("@")],
                    membership_started_at=now,
                    membership_expires_at=now + timedelta(days=days),
                    created_at=now,
                    updated_at=now,
                    moderation_status=User.MODERATION_STATUS_INTRO,
                ),
            )
            send_invited_email(request.me, user)
            return render(request, "message.html", {
                "title": "🎁 Юзер приглашен",
                "message": f"Сейчас он получит на почту '{email}' уведомление об этом. "
                           f"Ему будет нужно залогиниться по этой почте и заполнить интро."
            })
    else:
        form = GodmodeInviteForm()

    return render(request, "admin/simple_form.html", {"form": form})
