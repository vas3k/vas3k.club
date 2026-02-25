from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from authn.decorators.auth import require_auth
from fun.antics import AnticBase, ANTICS_MAP
from users.models.user import User


@csrf_exempt
@require_auth
def do_fun_antic(request):
    if request.method != "POST":
        raise Http404()

    recipient = request.POST.get("recipient")
    if recipient is not None:
        recipient = get_object_or_404(User, slug=recipient)

    antic_type = request.POST.get("antic_type")
    if antic_type in ANTICS_MAP:
        result = ANTICS_MAP[antic_type].handle(request.me, recipient)
    else:
        result = AnticBase.make_message(AnticBase.default_errors)

    return render(request, "message.html", result)
