import json

from django import template

from map.models import geo_coordinates

register = template.Library()


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


@register.simple_tag()
def map_messages_geo_json(messages, user=None):
    """Build GeoJSON FeatureCollection from MapMessages objects."""
    return json.dumps({
        "type": "FeatureCollection",
        "id": "map-messages",
        "features": [message.to_geojson_feature(user) for message in messages],
    })


@register.simple_tag()
def rooms_map_geo_json(rooms):
    """Build GeoJSON FeatureCollection of geo chat room markers."""
    features = []
    for room in rooms:
        feature = room.to_map_marker_feature()
        if feature:
            features.append(feature)
    return json.dumps({
        "type": "FeatureCollection",
        "id": "room-markers",
        "features": features,
    })
