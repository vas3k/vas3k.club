from django.shortcuts import redirect, render

from auth.helpers import auth_required
from users.models.user import User


@auth_required
def on_review(request):
    if request.me.moderation_status == User.MODERATION_STATUS_APPROVED:
        return redirect("profile", request.me.slug)
    return render(request, "users/messages/on_review.html")


@auth_required
def rejected(request):
    return render(request, "users/messages/rejected.html")


@auth_required
def banned(request):
    return render(request, "users/messages/banned.html")
