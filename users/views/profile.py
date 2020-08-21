from datetime import datetime, timedelta

import stripe
from django.conf import settings
from django.http import Http404
from django.shortcuts import redirect, get_object_or_404, render

from auth.helpers import auth_required
from comments.models import Comment
from common.pagination import paginate
from common.request import ajax_request
from posts.models import Post
from search.models import SearchIndex
from users.forms.profile import UserEditForm, NotificationsEditForm, ExpertiseForm
from users.models.achievements import UserAchievement
from users.models.expertise import UserExpertise
from users.models.geo import Geo
from users.models.tags import Tag, UserTag
from users.models.user import User
from utils.strings import random_hash


@auth_required
def profile(request, user_slug):
    if user_slug == "me":
        return redirect("profile", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)

    if not request.me.is_moderator:
        # hide unverified users
        if user.moderation_status != User.MODERATION_STATUS_APPROVED:
            raise Http404()

    if user.id == request.me.id:
        goto = request.GET.get("goto")
        if goto and goto.startswith(settings.APP_HOST):
            return redirect(goto)

    tags = Tag.objects.filter(is_visible=True).all()

    intro = Post.get_user_intro(user)
    projects = Post.objects.filter(author=user, type=Post.TYPE_PROJECT, is_visible=True).all()
    active_tags = {t.tag_id for t in UserTag.objects.filter(user=user).all()}
    achievements = UserAchievement.objects.filter(user=user).select_related("achievement")
    expertises = UserExpertise.objects.filter(user=user).all()
    comments = Comment.visible_objects().filter(author=user, post__is_visible=True).order_by("-created_at")[:3]
    posts = Post.objects_for_user(request.me)\
        .filter(author=user, is_visible=True)\
        .exclude(type__in=[Post.TYPE_INTRO, Post.TYPE_PROJECT])

    return render(request, "users/profile.html", {
        "user": user,
        "intro": intro,
        "projects": projects,
        "tags": tags,
        "active_tags": active_tags,
        "achievements": [ua.achievement for ua in achievements],
        "expertises": expertises,
        "comments": comments,
        "posts": paginate(request, posts),
    })


@auth_required
def edit_profile(request, user_slug):
    if user_slug == "me":
        return redirect("edit_profile", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    if request.method == "POST":
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()

            SearchIndex.update_user_index(user)
            Geo.update_for_user(user)

            return redirect("profile", user.slug)
    else:
        form = UserEditForm(instance=user)

    return render(request, "users/edit/profile.html", {"form": form, "user": user})


@auth_required
def edit_notifications(request, user_slug):
    if user_slug == "me":
        return redirect("edit_notifications", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    if request.method == "POST":
        form = NotificationsEditForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            return redirect("profile", user.slug)
    else:
        form = NotificationsEditForm(instance=user)

    return render(request, "users/edit/notifications.html", {"form": form, "user": user})


@auth_required
def edit_payments(request, user_slug):
    if user_slug == "me":
        return redirect("edit_payments", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    top_users = User.objects\
        .filter(
            moderation_status=User.MODERATION_STATUS_APPROVED,
            membership_expires_at__gte=datetime.utcnow() + timedelta(days=70)
        )\
        .order_by("-membership_expires_at")[:25]

    subscriptions = []
    if user.stripe_id:
        stripe_subscriptions = stripe.Subscription.list(customer=user.stripe_id, limit=100)
        subscriptions = [dict(
            id=s["id"],
            next_charge_at=datetime.utcfromtimestamp(s["current_period_end"]),
            amount=int(s["plan"]["amount"] / 100),
            interval=s["plan"]["interval"],
        ) for s in stripe_subscriptions["data"]]

    return render(request, "users/edit/payments.html", {
        "user": user,
        "subscriptions": subscriptions,
        "top_users": top_users,
    })


@auth_required
def edit_auth(request, user_slug):
    if user_slug == "me":
        return redirect("edit_auth", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id:
        raise Http404()

    if request.method == "POST" and request.POST.get("regenerate"):
        user.secret_hash = random_hash(length=16)
        user.save()
        return redirect("edit_auth", request.me.slug, permanent=False)

    return render(request, "users/edit/auth.html", {"user": user})


@auth_required
def edit_bot(request, user_slug):
    if user_slug == "me":
        return redirect("edit_bot", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    return render(request, "users/edit/bot.html", {"user": user})


@auth_required
def edit_data(request, user_slug):
    if user_slug == "me":
        return redirect("edit_data", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_god:
        raise Http404()

    return render(request, "users/edit/data.html", {"user": user})


@auth_required
@ajax_request
def toggle_tag(request, tag_code):
    if request.method != "POST":
        raise Http404()

    tag = get_object_or_404(Tag, code=tag_code)

    user_tag, is_created = UserTag.objects.get_or_create(
        user=request.me, tag=tag, defaults=dict(name=tag.name)
    )

    if not is_created:
        user_tag.delete()

    SearchIndex.update_user_tags(request.me)

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
            UserExpertise.objects.filter(
                user=request.me, expertise=user_expertise.expertise
            ).delete()
            user_expertise.save()
            return {
                "status": "created",
                "expertise": {
                    "name": user_expertise.name,
                    "expertise": user_expertise.expertise,
                    "value": user_expertise.value,
                },
            }

    return {"status": "ok"}


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

    return {"status": "ok"}

