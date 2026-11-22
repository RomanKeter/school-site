from django.urls import path

from . import views

urlpatterns = [
    path("rewards/", views.rewards_home, name="rewards"),
]
