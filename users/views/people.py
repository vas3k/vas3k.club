from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.postgres.search import SearchQuery
from django.core.cache import cache
from django.db.models import Count
from django.shortcuts import render

from authn.decorators.auth import require_auth
from common.models import group_by
from common.pagination import paginate
from tags.models import Tag
from users.models.user import User

TAGS_CACHE_TIMEOUT_SECONDS = 24 * 60 * 60


def _top(queryset, field, skip=None, limit=5):
    qs = queryset.exclude(**{field: None}).exclude(**{field: ""})
    if skip:
        qs = qs.exclude(**{f"{field}__in": skip})
    return list(
        qs.values(field)
          .annotate(count=Count(field))
          .order_by("-count")
          .values_list(field, "count")[:limit]
    )


@require_auth
def people(request):
    users = User.registered_members().order_by("-created_at")

    query = request.GET.get("query")
    if query:
        users = users.filter(
            index__index=(
                SearchQuery(query, config="simple", search_type="websearch") |
                SearchQuery(query, config="russian", search_type="websearch")
            )
        )

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

        if "friends" in filters:
            users = users.filter(friends_to__user_from=request.me)

    tag_stat_groups = cache.get("people_tag_stat_groups")
    tags_with_stats = cache.get("people_tags_with_stats")
    if not tag_stat_groups or not tags_with_stats:
        tags_with_stats = Tag.tags_with_stats()
        tag_stat_groups = group_by(tags_with_stats, "group", todict=True)
        tag_stat_groups.update({
            "travel": [tag for tag in tag_stat_groups.get(Tag.GROUP_CLUB, []) if tag.code in {
                "can_coffee", "can_city", "can_beer", "can_office", "can_sleep",
            }],
            "grow": [tag for tag in tag_stat_groups.get(Tag.GROUP_CLUB, []) if tag.code in {
                "can_advice", "can_project", "can_teach", "search_idea",
                "can_idea", "can_invest", "search_mentor", "can_mentor", "can_hobby"
            }],
            "work": [tag for tag in tag_stat_groups.get(Tag.GROUP_CLUB, []) if tag.code in {
                "can_refer", "search_employees", "search_job", "search_remote", "search_relocate"
            }],
            "collectible": [
                tag for tag in tag_stat_groups.get(Tag.GROUP_COLLECTIBLE, []) if tag.user_count > 1
            ][:20]
        })
        cache.set("people_tag_stat_groups", tag_stat_groups, TAGS_CACHE_TIMEOUT_SECONDS)
        cache.set("people_tags_with_stats", tags_with_stats, TAGS_CACHE_TIMEOUT_SECONDS)

    active_countries = User.registered_members().filter(country__isnull=False)\
        .exclude(country="")\
        .values("country")\
        .annotate(country_count=Count("country"))\
        .order_by("-country_count")

    users_total = users.count()

    map_stat_groups = {
        "💼 Топ компаний": _top(users, "company", skip={"-"}),
        "🌍 Страны": _top(users, "country"),
        "🏰 Города": _top(users, "city"),
    }

    users_for_map = users.filter(geo__isnull=False)

    return render(request, "users/people.html", {
        "people_query": {
            "query": query,
            "country": country,
            "tags": tags,
            "filters": filters,
        },
        "users_total": users_total,
        "users_for_map": users_for_map,
        "users_paginated": paginate(request, users, page_size=settings.PEOPLE_PAGE_SIZE),
        "tag_stat_groups": tag_stat_groups,
        "max_tag_user_count": max(tag.user_count for tag in tags_with_stats),
        "active_countries": active_countries,
        "map_stat_groups": map_stat_groups,
    })
