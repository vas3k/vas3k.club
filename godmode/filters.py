from django.db.models import Q
from django.db import models


FILTER_OPERATORS = [
    {"value": "contains", "label": "содержит", "lookup": "icontains"},
    {"value": "starts_with", "label": "начинается с", "lookup": "istartswith"},
    {"value": "ends_with", "label": "заканчивается на", "lookup": "iendswith"},
    {"value": "=", "label": "=", "lookup": "icontains"},
    {"value": ">", "label": ">", "lookup": "gt"},
    {"value": "<", "label": "<", "lookup": "lt"},
]


def apply_filters(queryset, model, filter_field, filter_operator, filter_value, sort_field=None, sort_direction=None):
    """
    Apply filters and sorting to a queryset.
    """
    if filter_value:
        if filter_field == "" or filter_field == "any":
            queryset = apply_any_field_filter(queryset, model, filter_value)
        else:
            queryset = apply_field_filter(queryset, model, filter_field, filter_operator, filter_value)

    # Apply sorting
    if sort_field and sort_direction:
        if sort_direction == "desc":
            queryset = queryset.order_by(f"-{sort_field}")
        else:
            queryset = queryset.order_by(sort_field)

    return queryset


def apply_any_field_filter(queryset, model, filter_value):
    """
    Search across all fields by converting them to text.
    """
    # Get all fields that can be converted to text
    text_fields = []
    for field in model._meta.fields:
        if isinstance(field, (models.CharField, models.TextField, models.EmailField,
                             models.IntegerField, models.DecimalField, models.FloatField,
                             models.DateField, models.DateTimeField, models.BooleanField)):
            text_fields.append(field.name)

    if not text_fields:
        return queryset

    # Create Q objects for each field
    q_objects = Q()
    for field_name in text_fields:
        q_objects |= Q(**{f"{field_name}__icontains": filter_value})

    return queryset.filter(q_objects)


def apply_field_filter(queryset, model, filter_field, filter_operator, filter_value):
    """
    Apply filter to a specific field using Django's built-in lookups.
    """
    try:
        # Find the operator in FILTER_OPERATORS
        operator_info = next((op for op in FILTER_OPERATORS if op["value"] == filter_operator), None)
        if not operator_info:
            return queryset

        lookup = operator_info["lookup"]

        # Special case for "=" operator on non-text fields
        if filter_operator == "=":
            field = model._meta.get_field(filter_field)
            if not isinstance(field, (models.CharField, models.TextField, models.EmailField)):
                lookup = ""

        # Build the filter kwargs
        if lookup:
            filter_kwargs = {f"{filter_field}__{lookup}": filter_value}
        else:
            filter_kwargs = {filter_field: filter_value}

        return queryset.filter(**filter_kwargs)

    except:
        # If field doesn't exist, ignore the filter
        return queryset


def get_filterable_fields(model):
    """
    Get list of fields that can be used for filtering.
    """
    filter_fields = [{"value": "", "label": "Любое поле"}]

    for field in model._meta.fields:
        filter_fields.append({
            "value": field.name,
            "label": field.verbose_name if field.verbose_name else field.name.replace('_', ' ').title()
        })

    return filter_fields
