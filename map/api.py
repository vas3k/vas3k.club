from django.db import transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from club.exceptions import ApiBadRequest
from map.models import MapMessages, MapMessageVote

MIN_LATITUDE, MAX_LATITUDE = -90.0, 90.0
MIN_LONGITUDE, MAX_LONGITUDE = -180.0, 180.0


@api(require_auth=True)
@require_http_methods(["POST"])
def api_create_map_message(request):
    text = (request.POST.get("text") or "").strip()
    if not text:
        raise ApiBadRequest(title="Пустое сообщение", message="Напишите хоть что-нибудь")

    if len(text) > MapMessages.MAX_TEXT_LENGTH:
        raise ApiBadRequest(
            title="Слишком длинное сообщение",
            message=f"Максимальная длина — {MapMessages.MAX_TEXT_LENGTH} символов",
        )

    try:
        latitude = float(request.POST.get("latitude"))
        longitude = float(request.POST.get("longitude"))
    except (TypeError, ValueError):
        raise ApiBadRequest(title="Непонятные координаты", message="Выберите точку на карте еще раз")

    if not MIN_LATITUDE <= latitude <= MAX_LATITUDE or not MIN_LONGITUDE <= longitude <= MAX_LONGITUDE:
        raise ApiBadRequest(title="Координаты вне карты", message="Выберите точку на карте еще раз")

    # lock the author row so two parallel posts cannot both pass can_post()
    with transaction.atomic():
        type(request.me).objects.select_for_update().get(pk=request.me.pk)
        if not MapMessages.can_post(request.me):
            raise ApiBadRequest(
                title="Подождите 24 часа",
                message="Оставлять сообщения на карте можно раз в сутки",
            )

        message = MapMessages.objects.create(
            author=request.me,
            text=text,
            latitude=latitude,
            longitude=longitude,
        )

    return {
        "status": "created",
        "feature": message.to_geojson_feature(request.me),
        "can_post": MapMessages.can_post(request.me),
    }


@api(require_auth=True)
@require_http_methods(["POST"])
def api_upvote_map_message(request, message_id):
    message = get_object_or_404(MapMessages, id=message_id)

    if message.author_id == request.me.id:
        raise ApiBadRequest(title="Это ваше сообщение", message="За свои сообщения голосовать нельзя")

    _, is_created = MapMessageVote.upvote(user=request.me, message=message, request=request)

    return {
        "upvotes": message.upvotes + (1 if is_created else 0),
        "is_voted": True,
    }
