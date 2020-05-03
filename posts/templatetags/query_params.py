from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def append_query_param(context, **kwargs):
    query_params = dict(context.request.GET.items())
    query_params.update(kwargs)
    return "?" + urlencode(query_params)
