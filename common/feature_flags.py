from django.shortcuts import render


def require_feature(feature_flag):
    def decorator(view):
        def wrapper(request, *args, **kwargs):
            if not feature_flag:
                return render(request, "common/messages/feature_required.html")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


def feature_switch(feature_flag, yes, no):
    def result(*args, **kwargs):
        if feature_flag:
            return yes(*args, **kwargs)
        else:
            return no(*args, **kwargs)
    return result


def noop(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
