from django import template

register = template.Library()


@register.inclusion_tag("common/paginator.html")
def paginator(items):
    adjacent_pages = 4
    num_pages = items.paginator.num_pages
    page = items.number

    start_page = max(page - adjacent_pages, 1)
    if start_page <= 3:
        start_page = 1

    end_page = page + adjacent_pages + 1

    if end_page >= num_pages - 1:
        end_page = num_pages + 1

    page_numbers = [n for n in range(start_page, end_page) if 0 < n <= num_pages]

    return {
        "items": items,
        "page_numbers": page_numbers,
        "show_first": 1 not in page_numbers,
        "show_last": num_pages not in page_numbers,
        "num_pages": num_pages,
    }
