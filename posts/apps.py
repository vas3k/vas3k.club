from django.apps import AppConfig


class PostsConfig(AppConfig):
    name = "posts"

    def ready(self):
        self.schedule_periodic_tasks()

    def schedule_periodic_tasks(self):
        from django_q.models import Schedule
        from django_q.tasks import schedule
        schedule("posts.scheduled.update_post_hotness", schedule_type=Schedule.HOURLY)
