from authn.decorators.api import api
from clickers.models import Click

MAX_CLICKS_TO_RETURN = 100


@api(require_auth=True)
def api_clicker(request, clicker_id):
    if request.method == "POST":
        Click.toggle(request.me, clicker_id)

    clicks = Click.list(clicker_id)
    return {
        "count": clicks.count(),
        "is_clicked": any([c.user_id == request.me.id for c in clicks]),
        "clicks": [c.to_dict() for c in clicks[:MAX_CLICKS_TO_RETURN]],
    }
