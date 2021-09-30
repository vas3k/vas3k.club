import os

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render, redirect

from auth.helpers import auth_required
from club.exceptions import AccessDenied
from landing.forms import GodmodeNetworkSettingsEditForm, GodmodeDigestEditForm
from landing.models import GodSettings
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
