from django.contrib import admin

from .models import Badge, ChildBadge, StarTransaction, Streak

admin.site.register(Badge)
admin.site.register(ChildBadge)
admin.site.register(Streak)


@admin.register(StarTransaction)
class StarAdmin(admin.ModelAdmin):
    list_display = ("child", "amount", "source_type", "source_id", "day")
