from functools import wraps

from django.template.response import TemplateResponse


def render(request, template_name, context=None, content_type=None, status=None, using=None):
    """Drop-in replacement for django.shortcuts.render that returns TemplateResponse.

    TemplateResponse is lazy — the template is rendered after middleware runs.
    This allows JsonApiMiddleware to intercept context_data and return JSON instead.
    """
    return TemplateResponse(request, template_name, context or {},
                            content_type=content_type, status=status, using=using)


def wants_json(request):
    """Check if the client wants a JSON response."""
    if request.GET.get("format") == "json":
        return True
    accept = request.META.get("HTTP_ACCEPT", "")
    return "application/json" in accept


def json_context(extra_context_fn):
    """Decorator: inject extra data into TemplateResponse context for JSON requests.

    Useful for views that load data in template tags (not in the view function).
    Example:
        @json_context(lambda request: {"rooms": list(Room.objects.filter(is_visible=True))})
        def list_rooms(request):
            return render(request, "rooms/list_rooms.html")
    """
    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(request, *args, **kwargs):
            response = view_fn(request, *args, **kwargs)
            if wants_json(request) and hasattr(response, "context_data"):
                response.context_data.update(extra_context_fn(request, *args, **kwargs))
            return response
        return wrapper
    return decorator
