from django.urls import path

from . import views

urlpatterns = [
    path("ai/ask/<int:block_id>/<int:exercise_id>/", views.ask_masya, name="ai_ask"),
    path("ai/teach/", views.teach_list, name="ai_teach_list"),
    path("ai/teach/<int:skill_id>/", views.teach, name="ai_teach"),
    path("parent/ai/", views.parent_ai, name="parent_ai"),
]
