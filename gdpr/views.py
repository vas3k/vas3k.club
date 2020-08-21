from datetime import datetime

from django.conf import settings
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404

from auth.helpers import auth_required
from gdpr.archive import generate_data_archive
from gdpr.models import DataRequests
from users.models.user import User


@auth_required
def request_data(request, user_slug):
    if request.method != "POST":
        return redirect("edit_data", user_slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_god:
        raise Http404()

    latest_data_request = DataRequests.objects\
        .filter(user=user, type=DataRequests.TYPE_ARCHIVE)\
        .order_by("-created_at")

    if latest_data_request and latest_data_request.created_at > datetime.utcnow() - settings.GDPR_ARCHIVE_TIMEDELTA:
        return render(request, "error.html", {
            "title": "Вы уже запрашивали архив сегодня",
            "message": "Генерация архива — сложная задача, "
                       "потому нам приходится ограничивать количество запросов в день. "
                       "Попробуйте завтра!"
        })

    # TODO: async_task(generate_data_archive, user)
    generate_data_archive(user)

    DataRequests.objects.create(
        user=user,
        type=DataRequests.TYPE_ARCHIVE,
    )

    return render(request, "gdpr/messages/data_requested.html")


@auth_required
def request_delete_account(request, user_slug):
    if request.method != "POST":
        return redirect("edit_data", user_slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_god:
        raise Http404()

    # TODO: send email

    DataRequests.objects.create(
        user=user,
        type=DataRequests.TYPE_FORGET,
    )

    return render(request, "gdpr/messages/delete_account_requested.html")


@auth_required
def delete_account(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_god:
        raise Http404()

    if request.method == "POST":
        pass  # TODO: check code/secrets/signature and delete

    return render(request, "users/edit/delete_account.html", {
        "code": request.GET.get("code"),
        "secret": request.GET.get("secret"),
    })
