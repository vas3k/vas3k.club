from django.db import models


class GodSettings(models.Model):
    digest_intro = models.TextField(null=True)
    network_page = models.TextField(null=True)

    class Meta:
        db_table = "god_settings"
