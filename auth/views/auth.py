from django.core.cache import cache
from django.shortcuts import redirect, render

from auth.helpers import auth_required
from auth.models import Session


def login(request):
    if request.me:
        return redirect("profile", request.me.slug)
    return render(request, "auth/login.html")


@auth_required
def logout(request):
    token = request.COOKIES.get("token")
    Session.objects.filter(token=token).delete()
    cache.delete(f"token:{token}:session")
    return redirect("index")
