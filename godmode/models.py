from django.db import models


class ClubSettings(models.Model):
    code = models.CharField(primary_key=True, max_length=32, null=False, unique=True)
    value = models.TextField(null=True)

    class Meta:
        db_table = "settings"

    def __str__(self):
        return f"{self.code}: {self.value}"

    @classmethod
    def get(cls, code, default=None):
        try:
            setting = cls.objects.get(code=code.strip().lower())
            return setting.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set(cls, code, value):
        setting, _ = cls.objects.update_or_create(
            code=code.strip().lower(),
            defaults=dict(
                value=value
            )
        )
        return setting
