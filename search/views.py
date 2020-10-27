from django.conf import settings
from django.shortcuts import render, redirect

from auth.helpers import auth_required
from common.pagination import paginate
from search.models import SearchIndex

ALLOWED_TYPES = {"post", "comment", "user"}
ALLOWED_ORDERING = {"-rank", "-created_at", "created_at"}


@auth_required
def search(request):
    query = request.GET.get("q")
    if not query:
        return redirect("index")

    # fetch query results
    results = SearchIndex\
        .search(query)\
        .select_related("post", "user", "comment")

    # filter them by type
    content_type = request.GET.get("type")
    if content_type in ALLOWED_TYPES:
        results = results.filter(type=content_type)
    else:
        content_type = None

    # exclude all deleted comments
    if content_type == "comment" or content_type == None:
        results = results.exclude(comment__is_deleted=True)

    # ordering
    ordering = request.GET.get("ordering")
    if ordering not in ALLOWED_ORDERING:
        ordering = "-rank"

    results = results.order_by(ordering)

    return render(request, "search.html", {
        "type": content_type,
        "ordering": ordering,
        "query": query,
        "results": paginate(request, results, page_size=settings.SEARCH_PAGE_SIZE),
    })
