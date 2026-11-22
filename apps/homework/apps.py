from django.apps import AppConfig


class Config(AppConfig):
    name = "apps.homework"
    label = "homework"
    verbose_name = "Моя домашка (этап 2)"
    default_auto_field = "django.db.models.BigAutoField"
