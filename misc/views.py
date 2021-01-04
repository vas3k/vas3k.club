from datetime import timedelta, datetime
from urllib.parse import urlencode

import pytz
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_GET
from icalendar import Calendar, Event, Timezone

from auth.helpers import auth_required
from landing.models import GodSettings
from users.models.achievements import Achievement


@auth_required
def achievements(request):
    achievements = Achievement.objects.filter(is_visible=True)
    return render(request, "pages/achievements.html", {
        "achievements": achievements
    })


@auth_required
def network(request):
    secret_page_html = GodSettings.objects.first().network_page
    return render(request, "pages/network.html", {
        "page_html": secret_page_html,
    })


@require_GET
def robots(request):
    lines = [
        "User-agent: *",
        "Sitemap: https://vas3k.club/sitemap.xml",
        "Host: https://vas3k.club",
        "Disallow: /intro/"
        "Disallow: /user/"
        "Disallow: /people/"
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@auth_required
def generate_ical_invite(request):
    event_title = request.GET.get("title")
    event_date = request.GET.get("date")
    event_url = request.GET.get("url")
    event_location = request.GET.get("location")
    event_timezone = request.GET.get("timezone")

    if not event_title or not event_date or not event_timezone:
        return HttpResponse("No date, tz or title")

    event_date = datetime.fromisoformat(event_date).replace(tzinfo=pytz.timezone(event_timezone))

    cal = Calendar()
    event = Event()
    event.add("summary", event_title)
    event.add("dtstart", event_date)
    event.add("dtend", event_date + timedelta(hours=2))

    if event_url:
        event.add("description", f"{event_url}")

    if event_location:
        event.add("location", event_location)

    cal.add_component(event)

    response = HttpResponse(cal.to_ical(), content_type="application/force-download")
    response["Content-Disposition"] = "attachment; filename=ical_vas3k_club.ics"
    return response


@auth_required
def generate_google_invite(request):
    event_title = request.GET.get("title")
    event_date = request.GET.get("date")
    event_url = request.GET.get("url")
    event_location = request.GET.get("location")
    event_timezone = request.GET.get("timezone")

    if not event_title or not event_date or not event_timezone:
        return HttpResponse("No date, tz or title")

    event_date = datetime.fromisoformat(event_date)

    google_url_params = urlencode({
        "text": event_title,
        "dates": "{}/{}".format(
            event_date.strftime("%Y%m%dT%H%M%S"),
            (event_date + timedelta(hours=2)).strftime("%Y%m%dT%H%M%S"),
        ),
        "details": f"{event_url}",
        "location": event_location,
        "ctz": event_timezone,
    })

    return redirect(f"https://calendar.google.com/calendar/u/0/r/eventedit?{google_url_params}")
