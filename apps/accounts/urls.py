from django.urls import path

from . import views

urlpatterns = [
    path("", views.root, name="root"),
    path("start/", views.child_start, name="child_start"),
    path("start/<int:child_id>/", views.child_pictures, name="child_pictures"),
    path("parent/login/", views.ParentLoginView.as_view(), name="parent_login"),
    path("logout/", views.do_logout, name="logout"),
]
