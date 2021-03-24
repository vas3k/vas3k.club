from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.postgres.search import SearchQuery
from django.db.models import Count
from django.shortcuts import render

from auth.helpers import auth_required
from common.models import group_by, top
from common.pagination import paginate
from users.models.expertise import UserExpertise
from users.models.tags import Tag
from users.models.user import User


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

    users_total = users.count()

    if users_total < 200:
        user_expertise = UserExpertise.objects.filter(user_id__in=[u.id for u in users])
    else:
        user_expertise = UserExpertise.objects.all()

    map_stat_groups = {
        "💼 Топ компаний": top(users, "company", skip={"-"})[:5],
        "🏰 Города": top(users, "city")[:5],
        "🎬 Экспертиза": top(user_expertise, "name")[:5],
    }

    return render(request, "users/people.html", {
        "people_query": {
            "query": query,
            "country": country,
            "tags": tags,
            "filters": filters,
        },
        "users": users,
        "users_total": users_total,
        "users_paginated": paginate(request, users, page_size=settings.PEOPLE_PAGE_SIZE),
        "tag_stat_groups": tag_stat_groups,
        "max_tag_user_count": max(tag.user_count for tag in tags_with_stats),
        "active_countries": active_countries,
        "map_stat_groups": map_stat_groups,
    })
