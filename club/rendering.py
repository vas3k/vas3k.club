from functools import wraps

from django.template.response import TemplateResponse


def render(request, template_name, context=None, content_type=None, status=None, using=None):
    return TemplateResponse(request, template_name, context or {},
                            content_type=content_type, status=status, using=using)


def wants_json(request):
    if request.GET.get("format") == "json":
        return True
    accept = request.META.get("HTTP_ACCEPT", "")
    return "application/json" in accept


def json_context(extra_context_fn):
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(request, *args, **kwargs):
            response = view_fn(request, *args, **kwargs)
            if wants_json(request) and hasattr(response, "context_data"):
                response.context_data.update(extra_context_fn(request, *args, **kwargs))
            return response
        return wrapper
    return decorator
