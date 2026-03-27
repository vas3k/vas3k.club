from uuid import uuid4

from django.db import models

from users.models.user import User

MAX_CLICKER_ID_LEN = 40

class Click(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)

    user = models.ForeignKey(User, related_name="clicks", on_delete=models.CASCADE)
    clicker_id = models.CharField(max_length=MAX_CLICKER_ID_LEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "clicks"
        ordering = ["-created_at"]
        unique_together = ("user", "clicker_id")

    @classmethod
    def list(cls, clicker_id):
        return cls.objects.filter(clicker_id=clicker_id[:MAX_CLICKER_ID_LEN]).select_related("user")

    @classmethod
    def toggle(cls, user, clicker_id):
        click, is_created = cls.objects.get_or_create(user=user, clicker_id=clicker_id[:MAX_CLICKER_ID_LEN])
        if not is_created:
            click.delete()
            return False
        else:
            return True


    def to_dict(self):
        return {
            "user": self.user.to_dict(),
            "created_at": self.created_at.isoformat(),
        }
