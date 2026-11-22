from django.contrib import admin

from .models import AIQuery, AISettings, FeynmanSession, FeynmanTopic


@admin.register(AIQuery)
class AIQueryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "child", "kind", "provider", "refused", "tokens_in", "tokens_out", "cost_usd")
    list_filter = ("kind", "refused", "provider")
    readonly_fields = [f.name for f in AIQuery._meta.fields]


@admin.register(FeynmanTopic)
class FeynmanTopicAdmin(admin.ModelAdmin):
    list_display = ("skill", "enabled")


@admin.register(FeynmanSession)
class FeynmanSessionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "child", "skill", "rounds", "finished", "stars_awarded")


admin.site.register(AISettings)
