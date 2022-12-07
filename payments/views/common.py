from django.shortcuts import redirect, render


def membership_expired(request):
    if not request.me:
        return redirect("index")

    if request.me.is_active_membership:
        return redirect("profile", request.me.slug)

    return render(request, "payments/membership_expired.html")
