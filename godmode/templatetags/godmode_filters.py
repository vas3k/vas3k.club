from django import template
from django.db.models import ForeignKey

from godmode.admin import ClubAdminField
from godmode.config import ADMIN

register = template.Library()


@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return ""
    return dictionary.get(key, "")


@register.filter
def get_attr(obj, key):
    if obj is None:
        return ""
    return getattr(obj, key)


@register.filter
def render_list_field(item, field: ClubAdminField):
    if item is None:
        return ""

    value = getattr(item, field.name)

    if not field.list_template and isinstance(field.model_field, ForeignKey):
        custom_template = ADMIN.foreign_key_templates.get(field.model_field.related_model)
        if custom_template:
            field.list_template = custom_template

    return field.render_list(value)
