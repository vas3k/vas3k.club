from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        # register signals here
        from notifications.signals.posts import create_or_update_post  # NOQA
        from notifications.signals.comments import create_or_update_comment  # NOQA
