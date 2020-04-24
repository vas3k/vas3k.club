from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django_q.tasks import async_task

from auth.helpers import auth_required, moderator_role_required
from common.pagination import paginate
from common.request import ajax_request
from notifications.telegram.users import notify_profile_needs_review
from posts.models import Post
from users.admin import do_user_admin_actions
from users.forms.admin import UserAdminForm
from users.forms.profile import UserEditForm, ExpertiseForm
from users.forms.intro import UserIntroForm
from users.models import User, UserBadge, UserExpertise, UserTag, Tag


@auth_required
def intro(request):
    if request.me.is_profile_complete \
            and request.me.is_profile_reviewed \
            and not request.me.is_profile_rejected:
        return redirect("profile", request.me.slug)

    if request.method == "POST":
        form = UserIntroForm(request.POST, request.FILES, instance=request.me)
        if form.is_valid():
            user = form.save(commit=False)

            # send to moderation
            user.is_profile_complete = True
            user.is_profile_reviewed = False
            user.is_profile_rejected = False
            user.save()

            # create intro post
            intro_post = Post.upsert_user_intro(user, form.cleaned_data["intro"], is_visible=False)

            # notify moderators to review profile
            async_task(notify_profile_needs_review, user, intro_post)

            return redirect("on_review")
    else:
        existing_intro = Post.get_user_intro(request.me)
        form = UserIntroForm(
            instance=request.me,
            initial={"intro": existing_intro.text if existing_intro else ""},
        )

    return render(request, "users/intro.html", {"form": form})


@auth_required
def profile(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)

    if user.id == request.me.id:
        goto = request.GET.get("goto")
        if goto:
            return redirect(goto)

    tags = Tag.objects.filter(is_visible=True).all()

    intro = Post.get_user_intro(user)
    projects = Post.objects.filter(author=user, type=Post.TYPE_PROJECT).all()
    active_tags = {t.tag_id for t in UserTag.objects.filter(user=user).all()}
    achievements = UserBadge.objects.filter(user=user)[:8]
    expertises = UserExpertise.objects.filter(user=user).all()
    posts = Post.objects_for_user(request.me)\
        .filter(author=user, is_visible=True)\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_PROJECT])

    return render(request, "users/profile.html", {
        "user": user,
        "intro": intro,
        "projects": projects,
        "tags": tags,
        "active_tags": active_tags,
        "achievements": achievements,
        "expertise_form": ExpertiseForm(),
        "expertises": expertises,
        "posts": paginate(request, posts),
    })


@auth_required
def edit_profile(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    if request.method == "POST":
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            return redirect("profile", user.slug)
    else:
        form = UserEditForm(instance=user)

    return render(request, "users/edit.html", {"form": form})


@auth_required
@moderator_role_required
def admin_profile(request, user_slug):
    user = get_object_or_404(User, slug=user_slug)

    if request.method == "POST":
        form = UserAdminForm(request.POST, request.FILES)
        if form.is_valid():
            return do_user_admin_actions(request, user, form.cleaned_data)
    else:
        form = UserAdminForm()

    return render(request, "users/admin.html", {"user": user, "form": form})


@auth_required
@ajax_request
def toggle_tag(request, tag_code):
    if request.method != "POST":
        raise Http404()

    tag = get_object_or_404(Tag, code=tag_code)

    user_tag, is_created = UserTag.objects.get_or_create(
        user=request.me,
        tag=tag,
        defaults=dict(
            name=tag.name
        )
    )

    if not is_created:
        user_tag.delete()

    return {
        "status": "created" if is_created else "deleted",
        "tag": {"code": tag.code, "name": tag.name, "color": tag.color},
    }


@auth_required
@ajax_request
def add_expertise(request):
    if request.method == "POST":
        form = ExpertiseForm(request.POST)
        if form.is_valid():
            user_expertise = form.save(commit=False)
            user_expertise.user = request.me
            UserExpertise.objects.filter(user=request.me, expertise=user_expertise.expertise).delete()
            user_expertise.save()
            return {
                "status": "created",
                "expertise": {
                    "name": user_expertise.name,
                    "expertise": user_expertise.expertise,
                    "value": user_expertise.value,
                },
            }

    return {"status": "tipidor"}


@auth_required
@ajax_request
def delete_expertise(request, expertise):
    if request.method == "POST":
        UserExpertise.objects.filter(user=request.me, expertise=expertise).delete()
        return {
            "status": "deleted",
            "expertise": {
                "expertise": expertise,
            },
        }

    return {"status": "tipidor"}


@auth_required
def on_review(request):
    if request.me.is_profile_reviewed:
        return redirect("profile", request.me.slug)
    return render(request, "users/messages/on_review.html")


@auth_required
def rejected(request):
    return render(request, "users/messages/rejected.html")


@auth_required
def banned(request):
    return render(request, "users/messages/banned.html")
