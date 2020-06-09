from django.shortcuts import render

from auth.helpers import auth_required
from users.models.achievements import Achievement


@auth_required
def achievements(request):
    achievements = Achievement.objects.filter(is_visible=True)
    return render(request, "misc/achievements.html", {
        "achievements": achievements
    })


@auth_required
def network(request):
    return render(request, "network.html")
