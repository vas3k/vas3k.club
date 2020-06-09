from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.postgres.search import SearchQuery
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django_q.tasks import async_task

from auth.helpers import auth_required, moderator_role_required
from common.pagination import paginate
from common.request import ajax_request
from notifications.telegram.users import notify_profile_needs_review
from posts.models import Post
from comments.models import Comment
from search.models import SearchIndex
from users.admin import do_user_admin_actions
from users.forms.admin import UserAdminForm
from users.forms.intro import UserIntroForm
from users.forms.profile import UserEditForm, ExpertiseForm, NotificationsEditForm
from users.models.user import User
from users.models.expertise import UserExpertise
from users.models.achievements import UserAchievement
from users.models.tags import Tag, UserTag
from users.models.geo import Geo
from common.models import top, group_by


@auth_required
def intro(request):
    if request.me.moderation_status == User.MODERATION_STATUS_APPROVED:
        return redirect("profile", request.me.slug)

    if request.method == "POST":
        form = UserIntroForm(request.POST, request.FILES, instance=request.me)
        if form.is_valid():
            user = form.save(commit=False)

            # send to moderation
            user.moderation_status = User.MODERATION_STATUS_ON_REVIEW
            user.save()

            # create intro post
            intro_post = Post.upsert_user_intro(
                user, form.cleaned_data["intro"], is_visible=False
            )

            Geo.update_for_user(user)

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
    projects = Post.objects.filter(author=user, type=Post.TYPE_PROJECT).all()
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
def edit_bot(request, user_slug):
    if user_slug == "me":
        return redirect("edit_bot", request.me.slug, permanent=False)

    user = get_object_or_404(User, slug=user_slug)
    if user.id != request.me.id and not request.me.is_moderator:
        raise Http404()

    return render(request, "users/edit/bot.html", {"user": user})


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


@auth_required
def on_review(request):
    if request.me.moderation_status == User.MODERATION_STATUS_APPROVED:
        return redirect("profile", request.me.slug)
    return render(request, "users/messages/on_review.html")


@auth_required
def rejected(request):
    return render(request, "users/messages/rejected.html")


@auth_required
def banned(request):
    return render(request, "users/messages/banned.html")


@auth_required
def people(request):
    users = User.registered_members().order_by("-created_at").select_related("geo")

    query = request.GET.get("query")
    if query:
        users = users.filter(index__index=SearchQuery(query, config="russian"))

    tags = request.GET.getlist("tags")
    if tags:
        users = users.filter(index__tags__contains=tags)

    country = request.GET.get("country")
    if country:
        users = users.filter(country=country)

    filters = request.GET.getlist("filters")
    if filters:
        if "faang" in filters:
            users = users.filter(company__in=[
                "Facebook", "Apple", "Google", "Amazon", "Netflix", "Microsoft",
                "Фейсбук", "Гугл", "Амазон", "Нетфликс", "Майкрософт", "Микрософт"
            ])

        if "same_city" in filters:
            users = users.filter(city=request.me.city)

        if "activity" in filters:
            users = users.filter(last_activity_at__gte=datetime.utcnow() - timedelta(days=30))

    tags_with_stats = Tag.tags_with_stats()
    tag_stat_groups = group_by(tags_with_stats, "group", todict=True)
    tag_stat_groups.update({
        "travel": [tag for tag in tag_stat_groups[Tag.GROUP_CLUB] if tag.code in {
            "can_coffee", "can_city", "can_beer", "can_office", "can_sleep",
        }],
        "grow": [tag for tag in tag_stat_groups[Tag.GROUP_CLUB] if tag.code in {
            "can_advice", "can_project", "can_teach", "search_idea",
            "can_idea", "can_invest", "search_mentor", "can_mentor", "can_hobby"
        }],
        "work": [tag for tag in tag_stat_groups[Tag.GROUP_CLUB] if tag.code in {
            "can_refer", "search_employees", "search_job", "search_remote", "search_relocate"
        }],
    })

    active_countries = User.registered_members().filter(country__isnull=False)\
        .values("country")\
        .annotate(country_count=Count("country"))\
        .order_by("-country_count")

    map_stat_groups = {
        "💼 Топ компаний": top(users, "company")[:5],
        "🏰 Города": top(users, "city")[:5],
        "🎬 Экспертиза": top(UserExpertise.objects.filter(user_id__in=[u.id for u in users]), "name")[:5],
    }

    return render(request, "users/people.html", {
        "people_query": {
            "query": query,
            "country": country,
            "tags": tags,
            "filters": filters,
        },
        "users": users,
        "users_paginated": paginate(request, users, page_size=settings.PEOPLE_PAGE_SIZE),
        "tag_stat_groups": tag_stat_groups,
        "max_tag_user_count": max(tag.user_count for tag in tags_with_stats),
        "active_countries": active_countries,
        "map_stat_groups": map_stat_groups,
    })
