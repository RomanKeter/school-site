from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="parent_dashboard"),
    path("settings/", views.settings_view, name="parent_settings"),
    path("trust-device/", views.trust_device, name="trust_device"),
    path("add-child/", views.add_child, name="add_child"),
    path("assign/", views.assign_skill, name="assign_skill"),
]
