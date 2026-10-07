from django.apps import AppConfig


class UsersConfig(AppConfig):
    name = "apps.users"  # Python path
    label = "users"      # short name used in AUTH_USER_MODEL / FKs / migrations
