from django.conf import settings
from django.core.paginator import Paginator


def paginate(request, items):
    paginator = Paginator(items, settings.DEFAULT_PAGE_SIZE)
    page_number = request.GET.get("page") or 1
    return paginator.get_page(page_number)
