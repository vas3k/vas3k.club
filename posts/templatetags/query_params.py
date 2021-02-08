from copy import deepcopy
from urllib.parse import urlencode

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def append_query_param(context, **kwargs):
    query_params = deepcopy(context.request.GET.dict())
    query_params_tags = context.request.GET.getlist("tags")
    query_params.update(kwargs)

    query_params_for_urlencode = []
    for index, key in enumerate(query_params):
        if key != "tags":
            query_params_for_urlencode.append((key, query_params[key]))
    for tag in query_params_tags:
        query_params_for_urlencode.append(('tags', tag))

    return "?" + urlencode(query_params)
