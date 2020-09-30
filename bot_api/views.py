from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
from users.models.user import User


def process_user(request, user_slug, secret_hash):
    print(user_slug)
    user = User.objects.filter(slug=user_slug)
    print(User.objects.all())
    print(user)
    return HttpResponse("Hello!", status=200)
