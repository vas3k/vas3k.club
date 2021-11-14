from posts.models.topics import Topic


def topics(request):
    PAID_TOPICS = ("partners", "service", "tools")

    topics = Topic.objects.filter(is_visible=True).all()
    return {
        "topics": Topic.objects.filter(is_visible=True).exclude(slug__in=PAID_TOPICS),
        "topics_paid": Topic.objects.filter(is_visible=True, slug__in=PAID_TOPICS),
        "topics_map": {t.slug: t for t in topics},
    }
