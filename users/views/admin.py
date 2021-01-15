from django.shortcuts import get_object_or_404, render, redirect

from auth.helpers import auth_required, moderator_role_required
from users.admin import do_user_admin_actions
from users.forms.admin import UserAdminForm, UserInfoAdminForm
from users.models.user import User


@auth_required
@moderator_role_required
def admin_profile(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)

    if request.method == "POST":
        form = UserAdminForm(request.POST, request.FILES)
        if form.is_valid():
            do_user_admin_actions(request, user, form.cleaned_data)

        info_form = UserInfoAdminForm(request.POST, instance=user)
        if info_form.is_valid():
            info_form.save()

        return redirect("profile", user.slug)
    else:
        form = UserAdminForm()
        info_form = UserInfoAdminForm(instance=user)

    return render(request, "users/admin.html", {"user": user, "form": form, "info_form": info_form})
