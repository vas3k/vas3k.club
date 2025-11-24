from datetime import timedelta, datetime
from urllib.parse import urlencode

import pytz
import telegram
from django.db.models import Count, Q, Sum
from django.http import HttpResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET
from icalendar import Calendar, Event

from authn.decorators.auth import require_auth
from badges.models import UserBadge
from club.settings import CREWS
from misc.models import NetworkGroup
from notifications.telegram.common import send_telegram_message, Chat, render_html_message
from users.models.achievements import Achievement
from users.models.user import User


@require_auth
def stats(request):
    achievements = Achievement.objects\
        .annotate(user_count=Count('users'))\
        .filter(is_visible=True)\
        .filter(user_count__gt=0)\
        .exclude(code__in=["old", "parliament_member"])\
        .order_by('-user_count')

    latest_badges = UserBadge.objects\
        .select_related("badge", "to_user")\
        .order_by('-created_at')[:20]

    top_badges = list(filter(None.__ne__, [
        User.registered_members().filter(id=to_user).first() for to_user, _ in UserBadge.objects
        .filter(created_at__gte=datetime.utcnow() - timedelta(days=150))
        .values_list("to_user")
        .annotate(sum_price=Sum("badge__price_days"))
        .order_by("-sum_price")[:20]  # select more in case someone gets deleted
    ]))[:15]  # filter None

    top_users = User.objects\
        .filter(
            moderation_status=User.MODERATION_STATUS_APPROVED,
            membership_expires_at__gte=datetime.utcnow() + timedelta(days=70)
        )\
        .order_by("-membership_expires_at")[:64]

    return render(request, "pages/stats.html", {
        "achievements": achievements,
        "latest_badges": latest_badges,
        "top_badges": top_badges,
        "top_users": top_users,
    })


@require_auth
def crew(request):
    moderators = User.objects\
        .filter(Q(roles__contains=[User.ROLE_MODERATOR]) | Q(roles__contains=[User.ROLE_GOD]))\
        .order_by("-last_activity_at")

    parliament = User.objects.filter(achievements__achievement_id="parliament_member").order_by("?")
    ministers = User.objects.filter(achievements__achievement_id="vibe_minister").order_by("?")
    orgs = User.objects.filter(achievements__achievement_id="offline_org")

    return render(request, "pages/crew.html", {
        "moderators": moderators,
        "parliament": parliament,
        "ministers": ministers,
        "orgs": orgs,
    })


@require_auth
def write_to_crew(request, crew):
    if crew not in CREWS:
        raise Http404()

    if request.method == "POST":
        reason = request.POST.get("reason")
        text = request.POST.get("text")
        if not text:
            return render(request, "error.html", {
                "title": f"Надо написать какой-то текст",
                "message": "А то что мы будем читать-то?"
            })

        send_telegram_message(
            chat=Chat(id=CREWS[crew]["telegram_chat_id"]),
            text=render_html_message(
                template="crew_message.html",
                user=request.me,
                reason=reason,
                text=text[:10000].strip()
            ),
            parse_mode=telegram.ParseMode.HTML,
        )

        return render(request, "message.html", {
            "title": "✅ Ваше письмо отправлено",
            "message": "Мы его прочитаем и обсудим."
        })


    return render(request, "pages/write_to_crew.html", {
        "crew": CREWS[crew],
        "default_reason": request.GET.get("reason"),
    })


@require_auth
def show_achievement(request, achievement_code):
    achievement = get_object_or_404(Achievement, code=achievement_code)
    if not achievement.is_visible:
        raise Http404()

    users = User.objects.filter(achievements__achievement_id=achievement_code)

    return render(request, "achievements/show_achievement.html", {
        "achievement": achievement,
        "users": users,
    })


@require_auth
def network(request):
    network_groups = NetworkGroup.visible_objects()
    return render(request, "network/network.html", {
        "network": network_groups,
    })


@require_GET
def robots(request):
    lines = [
        "User-agent: *",
        "Sitemap: https://vas3k.club/sitemap.xml",
        "Host: https://vas3k.club",
        "Disallow: /intro/",
        "Disallow: /user/",
        "Disallow: /people/",
        "Clean-param: comment_order&goto /",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


@require_auth
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


@require_auth
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
