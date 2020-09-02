from posts.models.topics import Topic


def topics(request):
    topics = Topic.objects.filter(is_visible=True).all()
    return {
        "topics": Topic.objects.filter(is_visible=True).all(),
        "topics_map": {t.slug: t for t in topics},
    }
