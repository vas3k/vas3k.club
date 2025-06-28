from django.db import models


class ClubSettings(models.Model):
    digest_title = models.TextField(null=True)
    digest_intro = models.TextField(null=True)

    class Meta:
        db_table = "settings"
