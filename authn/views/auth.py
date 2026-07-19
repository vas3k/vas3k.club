from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from authn.cache import clear_auth_token_cache
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
    clear_auth_token_cache(token)
    return redirect("index")
