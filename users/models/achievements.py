from uuid import uuid4

from django.db import models

from users.models.user import User


class Achievement(models.Model):
    code = models.CharField(primary_key=True, max_length=32, null=False, unique=True)
    name = models.CharField(max_length=64, null=False)
    image = models.URLField(null=False)
    description = models.TextField()
    style = models.CharField(max_length=256, default="", null=True)

    index = models.IntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        db_table = "achievements"
        ordering = ["index"]

    def achievement_users(self):
        return User.objects\
            .filter(achievements__achievement_id=self.code)\
            .order_by("-achievements__created_at")


class UserAchievement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(User, related_name="achievements", db_index=True, on_delete=models.CASCADE)
    achievement = models.ForeignKey(Achievement, related_name="users", db_index=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_achievements"
        unique_together = [["achievement", "user"]]
