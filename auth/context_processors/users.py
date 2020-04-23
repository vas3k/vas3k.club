def me(request):
    return {"me": request.me, "my_session": request.my_session}
