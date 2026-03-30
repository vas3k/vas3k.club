from django.core.cache import cache
from django.db import models

CLUB_SETTINGS_CACHE_KEY = "club_settings"


class ClubSettings(models.Model):
    code = models.CharField(primary_key=True, max_length=32, null=False, unique=True)
    value = models.TextField(null=True)

    class Meta:
        db_table = "settings"

    def __str__(self):
        return f"{self.code}: {self.value}"

    @classmethod
    def _get_all(cls):
        return cache.get_or_set(
            CLUB_SETTINGS_CACHE_KEY,
            lambda: dict(cls.objects.values_list("code", "value")),
        )

    @classmethod
    def get(cls, code, default=None):
        return cls._get_all().get(code.strip().lower(), default)

    @classmethod
    def set(cls, code, value):
        setting, _ = cls.objects.update_or_create(
            code=code.strip().lower(),
            defaults=dict(
                value=value
            )
        )
        return setting

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache.delete(CLUB_SETTINGS_CACHE_KEY)

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        cache.delete(CLUB_SETTINGS_CACHE_KEY)
        return result
