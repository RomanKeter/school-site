from django.urls import path

from . import views

urlpatterns = [
    path("play/<int:block_id>/", views.play_block, name="play_block"),
    path("play/<int:block_id>/worked/", views.worked_next, name="worked_next"),
    path("play/<int:block_id>/ex/<int:exercise_id>/check/", views.check_exercise, name="check_exercise"),
    path("play/<int:block_id>/ex/<int:exercise_id>/hint/", views.hint, name="hint"),
    path("play/<int:block_id>/word/<int:word_id>/check/", views.check_word, name="check_word"),
    path("activity/ping/", views.activity_ping, name="activity_ping"),
    path("words/", views.dictionary, name="dictionary"),
    path("reflect/", views.reflect, name="reflect"),
]
