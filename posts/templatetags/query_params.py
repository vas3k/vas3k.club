from copy import deepcopy

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def append_query_param(context, **kwargs):
    query_params = deepcopy(context.request.GET)
    for param, value in kwargs.items():
        query_params[param] = value
    return "?" + query_params.urlencode()
