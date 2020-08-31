from uuid import uuid4

from django.db import models
from slugify import slugify

from common.data.colors import COOL_COLORS
from common.data.expertise import EXPERTISE_FLAT_MAP
from users.models.user import User


class UserExpertise(models.Model):
    EXPERTISE_SLUG_LENGTH = 32

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="expertise", on_delete=models.CASCADE)
    expertise = models.CharField(max_length=EXPERTISE_SLUG_LENGTH, null=False, db_index=True)
    name = models.CharField(max_length=64, null=False)
    value = models.IntegerField(default=0, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_expertise"
        unique_together = [["expertise", "user"]]
        ordering = ["created_at"]

    def save(self, *args, **kwargs):

        if not self.name:
            self.name = EXPERTISE_FLAT_MAP.get(self.expertise) or self.expertise

        if self.expertise not in EXPERTISE_FLAT_MAP:
            self.expertise = self.make_custom_expertise_slug(self.expertise)

        return super().save(*args, **kwargs)

    @property
    def color(self):
        return COOL_COLORS[hash(self.name) % len(COOL_COLORS)]

    @classmethod
    def make_custom_expertise_slug(cls, expertise_name: str):
        return slugify(expertise_name.lower())[:cls.EXPERTISE_SLUG_LENGTH]
