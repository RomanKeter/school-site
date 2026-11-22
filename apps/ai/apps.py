from django.apps import AppConfig


class Config(AppConfig):
    name = "apps.ai"
    label = "ai"
    verbose_name = "ИИ-помощник Мася (этап 2)"
    default_auto_field = "django.db.models.BigAutoField"
