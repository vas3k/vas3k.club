import json

from django.forms import model_to_dict
from django.http import HttpResponse, JsonResponse

from users.models.user import User


def process_user(request, secret_hash):
    if request.method != "POST":
        return HttpResponse(status=400)

    try:
        user = User.objects.get(secret_hash=secret_hash)
    except User.DoesNotExist:
        return HttpResponse(status=404)

    telegram_field_to_model_field_mapping = {
        "id": "telegram_id",
        "username": "telegram_data.username",
        "first_name": "telegram_data.first_name",
        "last_name": "telegram_data.last_name",
        "language_code": "telegram_data.language_code",
    }
    for telegram_field, model_field in telegram_field_to_model_field_mapping.items():
        setattr(user, model_field, request.POST[telegram_field])

    user.save()
    return JsonResponse(model_to_dict(user), status=200)
