from django.core.cache import cache
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from authn.decorators.auth import require_auth
from authn.models.session import Session


def join(request):
    if request.me:
        return redirect("profile", request.me.slug)

    return render(request, "auth/join.html")


def login(request):
    if request.me:
        return redirect("profile", request.me.slug)

    return render(request, "auth/login.html", {
        "goto": request.GET.get("goto"),
        "email": request.GET.get("email"),
    })


@require_auth
@require_http_methods(["POST"])
def logout(request):
    token = request.COOKIES.get("token")
    Session.objects.filter(token=token).delete()
    cache.delete(f"token:{token}:session")
    return redirect("index")
