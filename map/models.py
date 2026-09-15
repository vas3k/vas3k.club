import random
from datetime import datetime, timedelta
from uuid import uuid4

from django.db import models
from django.db.models import Exists, F, OuterRef, Q
from django.urls import reverse

from common.request import parse_ip_address


def geo_coordinates(geo):
    """Extract (latitude, longitude) from a geo dict, applying random offset for non-precise locations.

    Returns None if geo is missing or has no coordinates.
    """
    if not geo:
        return None
    lat = geo.get("latitude")
    lng = geo.get("longitude")
    if lat is None or lng is None:
        return None
    if not geo.get("precise"):
        lat += random.uniform(-0.12, 0.12)
        lng += random.uniform(-0.25, 0.25)
    return lat, lng


class Geo(models.Model):
    id = models.AutoField(primary_key=True)
    country_en = models.CharField(max_length=256)
    region_en = models.CharField(max_length=256)
    city_en = models.CharField(max_length=256, db_index=True)
    country = models.CharField(max_length=256)
    region = models.CharField(max_length=256)
    city = models.CharField(max_length=256, db_index=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    population = models.IntegerField(default=0)

    class Meta:
        db_table = "geo"
        ordering = ["id"]

    @classmethod
    def update_for_user(cls, user, fuzzy=False):
        if not user.country or not user.city:
            return

        geo = Geo.objects.filter(
            Q(country=user.country) & (Q(city__iexact=user.city) | Q(city_en__iexact=user.city))
        ).order_by("id").first()

        if not geo and fuzzy:
            geo = Geo.objects.filter(
                Q(country=user.country) & (Q(city__icontains=user.city) | Q(city_en__icontains=user.city))
            ).order_by("id").first()

        if geo:
            user.geo = {
                "latitude": geo.latitude,
                "longitude": geo.longitude,
            }
            user.save()


class MapMessages(models.Model):
    MAX_TEXT_LENGTH = 128
    POST_COOLDOWN = timedelta(hours=24)
    MAX_MESSAGES_ON_MAP = 1000
    POPULAR_UPVOTES = 10

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    author = models.ForeignKey("users.User", related_name="map_messages", on_delete=models.CASCADE)
    text = models.TextField()
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    upvotes = models.IntegerField(default=0, db_index=True)

    class Meta:
        db_table = "map_messages"
        ordering = ["-created_at"]

    @classmethod
    def objects_for_user(cls, user):
        return cls.objects.select_related("author").annotate(
            is_voted=Exists(MapMessageVote.objects.filter(message=OuterRef("pk"), user=user)),
        )

    @classmethod
    def visible_for_user(cls, user):
        latest = cls.objects.order_by("-created_at").values("id")[:cls.MAX_MESSAGES_ON_MAP]
        return cls.objects_for_user(user).filter(
            Q(id__in=latest) | Q(upvotes__gt=cls.POPULAR_UPVOTES)
        )

    @classmethod
    def can_post(cls, user):
        """Everyone gets one message a day, so nobody can spam the map"""
        if user.is_moderator or user.is_curator:
            return True

        return not cls.objects.filter(
            author=user,
            created_at__gte=datetime.utcnow() - cls.POST_COOLDOWN,
        ).exists()

    def increment_vote_count(self):
        return MapMessages.objects.filter(id=self.id).update(upvotes=F("upvotes") + 1)

    def to_geojson_feature(self, user=None):
        return {
            "type": "Feature",
            "properties": {
                "id": str(self.id),
                "text": self.text,
                "author_name": self.author.full_name,
                "author_url": f"/user/{self.author.slug}/",
                "author_avatar": self.author.get_avatar(),
                "upvotes": self.upvotes,
                "upvote_url": reverse("api_upvote_map_message", args=[self.id]),
                # only set on querysets from objects_for_user, the create api has nothing to look up
                "is_voted": bool(getattr(self, "is_voted", False)),
                "is_mine": bool(user) and user.id == self.author_id,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            },
        }


class MapMessageVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(
        "users.User", related_name="map_message_votes", db_index=True, null=True, on_delete=models.SET_NULL
    )
    message = models.ForeignKey(MapMessages, related_name="votes", db_index=True, on_delete=models.CASCADE)

    ipaddress = models.GenericIPAddressField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "map_message_votes"
        unique_together = [["user", "message"]]

    @classmethod
    def upvote(cls, user, message, request=None):
        """Votes are final: they can only be given once and never retracted"""
        if user.id == message.author_id:
            return None, False

        vote, is_vote_created = cls.objects.get_or_create(
            user=user,
            message=message,
            defaults=dict(
                ipaddress=parse_ip_address(request) if request else None,
            )
        )

        if is_vote_created:
            message.increment_vote_count()

        return vote, is_vote_created
