from django.core import serializers
from django import template

register = template.Library()

@register.filter()
def querySetToJson(querySet):
    return serializers.serialize('json', querySet)
