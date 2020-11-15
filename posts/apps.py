from django.apps import AppConfig
from django.conf import settings


class PostsConfig(AppConfig):
    name = "posts"

    def ready(self):
        if not settings.TESTS_RUN:
            self.schedule_periodic_tasks()

    def schedule_periodic_tasks(self):
        from django_q.models import Schedule
        from django_q.tasks import schedule
        schedule("posts.scheduled.update_post_hotness", schedule_type=Schedule.HOURLY)
