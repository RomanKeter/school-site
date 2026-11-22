from django.contrib import admin

from .models import ContentRequest, HomeworkRequest, SearchAlias


@admin.register(HomeworkRequest)
class HomeworkRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "child", "text", "match_method", "looks_like_task")
    list_filter = ("match_method",)


@admin.register(ContentRequest)
class ContentRequestAdmin(admin.ModelAdmin):
    list_display = ("created_at", "family", "text", "status")
    list_filter = ("status",)


@admin.register(SearchAlias)
class SearchAliasAdmin(admin.ModelAdmin):
    list_display = ("skill", "topic")
