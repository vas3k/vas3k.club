import json

from django import template

from tags.models import Tag

register = template.Library()


@register.simple_tag()
def user_tag_images(user):
    tags = user.tags.filter(tag__group=Tag.GROUP_HOBBIES)[:5]
    return " ".join([str(t.name.split(" ", 1)[0]) for t in tags])


@register.simple_tag()
def users_geo_json(users):
    return json.dumps({
        "type": "FeatureCollection",
        "id": "user-markers",
        "features": [{
            "type": "Feature",
            "properties": {
                "id": user.slug,
                "url": f"/user/{user.slug}/",
                "avatar": user.avatar,
            },
            "geometry": {
                "type": "Point",
                "coordinates": user.geo.to_json_coordinates(randomize=True),
            }
        } for user in users if user.geo]
    })
