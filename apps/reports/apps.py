from django.apps import AppConfig


class Config(AppConfig):
    name = "apps.reports"
    label = "reports"
    verbose_name = "Отчёты родителю (этап 2)"
    default_auto_field = "django.db.models.BigAutoField"
