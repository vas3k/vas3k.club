from django.utils.functional import SimpleLazyObject

from users.models.friends import Friend


def me(request):
    def my_friends_ids():
        return set(
            Friend.user_friends(request.me).values_list("user_to_id", flat=True)
        )

    return {
        "me": request.me,
        "friends_ids": SimpleLazyObject(my_friends_ids) if request.me else set(),
    }
