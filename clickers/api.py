from django.views.decorators.http import require_http_methods

from authn.decorators.api import api
from clickers.models import Click


@api(require_auth=True)
@require_http_methods(["GET", "POST", "DELETE"])
def api_clicker(request, clicker_id):
    clicker_id = clicker_id[:40]

    if request.method == "POST":
        Click.objects.get_or_create(user=request.me, clicker_id=clicker_id)
    elif request.method == "DELETE":
        Click.objects.filter(user=request.me, clicker_id=clicker_id).delete()

    clicks = Click.list(clicker_id)
    return {
        "count": clicks.count(),
        "is_clicked": any([c.user_id == request.me.id for c in clicks]),
        "clicks": [c.to_dict() for c in clicks[:100]],
    }
