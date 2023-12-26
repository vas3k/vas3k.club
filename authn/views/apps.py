from django.shortcuts import render, get_object_or_404, redirect

from authn.forms import AppForm
from authn.decorators.auth import require_auth
from authn.models.openid import OAuth2App, OAuth2Token, OAuth2AuthorizationCode
from club.exceptions import AccessDenied


@require_auth
def list_apps(request):
    user_apps = OAuth2App.objects.filter(owner=request.me).all()
    return render(request, "openid/list_apps.html", {
        "apps": user_apps,
    })


@require_auth
def create_app(request):
    if request.method == "POST":
        form = AppForm(request.POST)
        if form.is_valid():
            app = form.save(commit=False)
            app.owner = request.me
            app.save()
            return redirect("edit_app", app.id)
    else:
        form = AppForm()

    return render(request, "openid/create_app.html", {
        "form": form
    })


@require_auth
def edit_app(request, app_id):
    app = get_object_or_404(OAuth2App, id=app_id)
    if app.owner != request.me:
        raise AccessDenied()

    if request.method == "POST":
        form = AppForm(request.POST, instance=app)
        if form.is_valid():
            form.save()
            return redirect("apps")
    else:
        form = AppForm(instance=app)

    return render(request, "openid/edit_app.html", {
        "app": app,
        "form": form
    })


@require_auth
def delete_app(request, app_id):
    app = get_object_or_404(OAuth2App, id=app_id)
    if app.owner != request.me:
        raise AccessDenied()

    if request.method == "POST":
        OAuth2Token.objects.filter(client_id=app.client_id).delete()
        OAuth2AuthorizationCode.objects.filter(client_id=app.client_id).delete()
        app.delete()

    return redirect("apps")
