from django.urls import path

from . import views

urlpatterns = [path("preview/exercise/<int:pk>/", views.preview_exercise, name="preview_exercise")]
