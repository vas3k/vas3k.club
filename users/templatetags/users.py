import json

from django import template

from tags.models import Tag
from users.models.geo import geo_coordinates

register = template.Library()


@register.simple_tag()
def user_tag_images(user):
    tags = user.tags.filter(tag__group=Tag.GROUP_HOBBIES)[:5]
    return " ".join([str(t.name.split(" ", 1)[0]) for t in tags])


@register.simple_tag()
def users_geo_json(users):
    """Build GeoJSON FeatureCollection from values_list(slug, avatar, geo) tuples."""
    features = []
    for slug, avatar, geo in users:
        coords = geo_coordinates(geo)
        if not coords:
            continue
        lat, lng = coords
        features.append({
            "type": "Feature",
            "properties": {
                "id": slug,
                "url": f"/user/{slug}/",
                "avatar": avatar,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat],
            },
        })
    return json.dumps({
        "type": "FeatureCollection",
        "id": "user-markers",
        "features": features,
    })
