import logging

from django.apps import AppConfig

log = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    name = "users"
