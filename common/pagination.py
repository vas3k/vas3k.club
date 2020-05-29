from django.conf import settings
from django.core.paginator import Paginator


def paginate(request, items, page_size=settings.DEFAULT_PAGE_SIZE):
    paginator = Paginator(items, page_size)
    page_number = request.GET.get("page") or 1
    return paginator.get_page(page_number)
