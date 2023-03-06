from django.shortcuts import redirect, render

from authn.decorators.auth import require_auth
from users.models.user import User


@require_auth
def on_review(request):
    if request.me.moderation_status == User.MODERATION_STATUS_APPROVED:
        return redirect("profile", request.me.slug)
    return render(request, "users/messages/on_review.html")


@require_auth
def rejected(request):
    return render(request, "users/messages/rejected.html")


@require_auth
def banned(request):
    return render(request, "users/messages/banned.html")
