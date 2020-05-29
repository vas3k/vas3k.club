from django.conf import settings
from django.shortcuts import render, redirect

from auth.helpers import auth_required
from common.pagination import paginate
from search.models import SearchIndex


@auth_required
def search(request):
    query = request.GET.get("q")
    if not query:
        return redirect("index")

    results = SearchIndex.search(query).select_related("post", "profile", "comment")

    return render(request, "search.html", {
        "query": query,
        "results": paginate(request, results, page_size=settings.SEARCH_PAGE_SIZE),
    })
