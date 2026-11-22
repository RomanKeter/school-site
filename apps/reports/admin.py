from django.contrib import admin

from .models import DinnerTip, NotificationLog, WeeklyReport


@admin.register(DinnerTip)
class DinnerTipAdmin(admin.ModelAdmin):
    list_display = ("subject", "is_active", "text")
    list_filter = ("subject", "is_active")


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ("child", "week_start", "sent_at", "is_test")
    list_filter = ("is_test",)


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("sent_at", "parent", "kind", "status", "error")
    list_filter = ("kind", "status")
