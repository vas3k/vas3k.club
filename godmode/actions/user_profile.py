from django.shortcuts import redirect

from users.models.user import User


def view_profile_action(request, user: User, **context):
    return redirect(user.get_absolute_url())
