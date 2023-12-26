from django.http import Http404
from django.shortcuts import get_object_or_404, redirect

from authn.decorators.auth import require_auth
from users.models.notes import UserNote
from users.models.user import User


@require_auth
def edit_note(request, user_slug):
    if request.method != "POST":
        raise Http404()

    user_to = get_object_or_404(User, slug=user_slug)
    text = request.POST.get("text") or ""

    if not text.strip():
        UserNote.objects.filter(
            user_from=request.me,
            user_to=user_to
        ).delete()
    else:
        UserNote.objects.update_or_create(
            user_from=request.me,
            user_to=user_to,
            defaults=dict(
                text=text.strip()
            )
        )

    return redirect("profile", user_slug)
