from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        # register signals here
        from notifications.signals.achievements import create_or_update_achievement  # NOQA
        from notifications.signals.posts import create_or_update_post  # NOQA
        from notifications.signals.comments import create_or_update_comment  # NOQA
        from notifications.signals.users import create_or_update_user  # NOQA
        from notifications.signals.badges import create_or_update_badge  # NOQA
