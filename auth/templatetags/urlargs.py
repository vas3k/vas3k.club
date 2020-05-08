from django import template
from django.urls import reverse

from django import template
from django.utils.encoding import escape_uri_path

register = template.Library()


@register.simple_tag()
def urlargs(url, **kwargs):
    url = reverse(url)
    qs = '&'.join([f"{k}={escape_uri_path(v)}" for k, v in kwargs.items()])
    return '?'.join((url, qs))
