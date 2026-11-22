from django.contrib import admin

from .models import ReviewItem, ReviewLog, SrsConfig

admin.site.register(SrsConfig)


@admin.register(ReviewItem)
class ReviewItemAdmin(admin.ModelAdmin):
    list_display = ("child", "item_type", "skill", "word", "n", "ease_factor", "interval_days", "due_date")
    list_filter = ("item_type", "child")


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = ("review_item", "reviewed_at", "q", "ef_before", "ef_after", "interval_before", "interval_after")
