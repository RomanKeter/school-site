from django.urls import path

from . import views

urlpatterns = [
    path("homework/", views.homework, name="homework"),
    path("homework/<int:req_id>/start/", views.start, name="homework_start"),
    path("parent/homework/", views.parent_homework, name="parent_homework"),
]
