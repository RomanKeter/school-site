from django.apps import AppConfig


class Config(AppConfig):
    name = "apps.content"
    label = "content"
    default_auto_field = "django.db.models.BigAutoField"
