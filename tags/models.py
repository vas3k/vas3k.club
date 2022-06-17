from uuid import uuid4

from django.db import models

from common.data.colors import COOL_COLORS
from users.models.user import User


class Tag(models.Model):
    GROUP_HOBBIES = "hobbies"
    GROUP_PERSONAL = "personal"
    GROUP_TECH = "tech"
    GROUP_CLUB = "club"
    GROUP_COLLECTIBLE = "collectible"
    GROUP_OTHER = "other"
    GROUPS = [
        (GROUP_PERSONAL, "Я"),
        (GROUP_TECH, "Технологии"),
        (GROUP_CLUB, "Для других членов Клуба я..."),
        (GROUP_HOBBIES, "Хобби"),
        (GROUP_COLLECTIBLE, "Коллекционные теги"),
        (GROUP_OTHER, "Другие"),
    ]

    code = models.CharField(primary_key=True, max_length=32, null=False, unique=True)
    group = models.CharField(max_length=32, choices=GROUPS, default=GROUP_OTHER, null=False)
    name = models.CharField(max_length=64, null=False)

    index = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "tags"
        ordering = ["-group", "index"]

    def to_dict(self):
        return {
            "code": self.code,
            "group": self.group,
            "name": self.name,
            "color": self.color,
        }

    @property
    def color(self):
        return COOL_COLORS[sum(map(ord, self.code)) % len(COOL_COLORS)]

    def group_display(self):
        return dict(Tag.GROUPS).get(self.group) or Tag.GROUP_OTHER

    @classmethod
    def tags_with_stats(cls):
        # to show fancy charts on /people/ page
        return Tag.objects.filter(is_visible=True).extra({
            "user_count": "select count(*) from user_tags where user_tags.tag_id = tags.code"
        })


class UserTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="tags", on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, related_name="user_tags", on_delete=models.CASCADE)
    name = models.CharField(max_length=64, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_tags"
        unique_together = [["tag", "user"]]
