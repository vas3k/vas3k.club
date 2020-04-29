from django.http import JsonResponse, Http404
from django.shortcuts import redirect


def parse_ip_address(request):
    ipaddress = request.META.get("HTTP_X_REAL_IP") \
        or request.META.get("HTTP_X_FORWARDED_FOR") \
        or request.environ.get("REMOTE_ADDR") or ""

    if "," in ipaddress:  # multiple ips in the header
        ipaddress = ipaddress.split(",", 1)[0]
    return ipaddress


def parse_useragent(request):
    return (request.META.get("HTTP_USER_AGENT") or "")[:512]


def is_ajax(request):
    return bool(request.GET.get("is_ajax"))


def ajax_request(view):
    def wrapper(request, *args, **kwargs):
        status_code = 200
        try:
            results = view(request, *args, **kwargs)
        except Http404:
            status_code = 404
            results = {"error": "Not Found"}

        if is_ajax(request):
            return JsonResponse(data=results, status=status_code)
        else:
            return redirect(request.META.get("HTTP_REFERER") or "/")

    return wrapper
