import os

from django.conf import settings
from django.http import Http404
from django.shortcuts import render

from auth.helpers import auth_required
from club.exceptions import AccessDenied
from landing.forms import GodSettingsEditForm
from landing.models import GodSettings

EXISTING_DOCS = [
    os.path.splitext(f)[0]  # get only filenames
    for f in os.listdir(os.path.join(settings.BASE_DIR, "frontend/html/docs"))
    if f.endswith(".html")
]


def landing(request):
    return render(request, "landing.html")


def docs(request, doc_slug):
    if doc_slug not in EXISTING_DOCS:
        raise Http404()

    return render(request, f"docs/{doc_slug}.html")


@auth_required
def god_settings(request):
    if not request.me.is_god:
        raise AccessDenied()

    god_settings = GodSettings.objects.first()

    if request.method == "POST":
        form = GodSettingsEditForm(request.POST, request.FILES, instance=god_settings)
        if form.is_valid():
            form.save()
    else:
        form = GodSettingsEditForm(instance=god_settings)

    return render(request, "admin/godmode.html", {"form": form})
