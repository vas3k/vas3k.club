from uuid import uuid4

from django.db import models
from slugify import slugify

from common.data.colors import COOL_COLORS
from common.data.expertise import EXPERTISE
from users.models.user import User


class UserExpertise(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="expertise", on_delete=models.CASCADE)
    expertise = models.CharField(max_length=32, null=False, db_index=True)
    name = models.CharField(max_length=64, null=False)
    value = models.IntegerField(default=0, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_expertise"
        unique_together = [["expertise", "user"]]
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        pre_defined_expertise = dict(sum([e[1] for e in EXPERTISE], []))  # flatten nested items

        if not self.name:
            self.name = pre_defined_expertise.get(self.expertise) or self.expertise

        if self.expertise not in pre_defined_expertise:
            self.expertise = slugify(self.expertise.lower())[:32]

        return super().save(*args, **kwargs)

    @property
    def color(self):
        return COOL_COLORS[hash(self.name) % len(COOL_COLORS)]
