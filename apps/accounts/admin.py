from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import ChildProfile, ChildSettings, Family, ParentProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Роль", {"fields": ("role",)}),)
    list_display = ("username", "email", "role", "is_staff")


admin.site.register(Family)
admin.site.register(ParentProfile)


class SettingsInline(admin.StackedInline):
    model = ChildSettings


@admin.register(ChildProfile)
class ChildAdmin(admin.ModelAdmin):
    list_display = ("display_name", "family", "grade", "avatar_code")
    exclude = ("picture_password_hash",)
    inlines = [SettingsInline]
