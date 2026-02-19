from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from authn.decorators.auth import require_auth
from fun.handlers import ANTIC_HANDLERS
from users.models.user import User


@csrf_exempt
@require_auth
def do_fun_antic(request):
    if request.method != "POST":
        raise Http404()

    antic_type = request.GET.get("antic_type")
    if antic_type not in ANTIC_HANDLERS:
        antic_type = "miss"
    handler = ANTIC_HANDLERS[antic_type]

    recipient = request.GET.get("recipient")
    if recipient is not None:
        recipient = get_object_or_404(User, slug=recipient)

    success, result = handler(request.me, recipient)
    return render(
        request,
        "message.html" if success else "error.html",
        result
    )
