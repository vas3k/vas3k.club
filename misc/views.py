from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

from auth.helpers import auth_required
from landing.models import GodSettings
from common.request import ajax_request
from users.models.achievements import Achievement

from common.markdown.markdown import markdown_text
from common.markdown.email_renderer import EmailRenderer
from common.markdown.club_renderer import ClubRenderer
from common.markdown.plain_renderer import PlainRenderer

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
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

@ajax_request
def preview_md(request):
    if request.method != "POST":
        raise Http404()

    renderer = request.GET.get("renderer", "club")
    text = request.POST.get("markdownPlaintext", '')

    renderer_map = {'mail': EmailRenderer, 'plain': PlainRenderer, 'club': ClubRenderer}

    return {
        "markdown": markdown_text(text, renderer_map.get(renderer, ClubRenderer))
    }
