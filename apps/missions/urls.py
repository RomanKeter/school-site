from django.urls import path

from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path("mission/start/", views.start_mission, name="start_mission"),
    path("map/<slug:subject_code>/", views.map_view, name="map"),
]
