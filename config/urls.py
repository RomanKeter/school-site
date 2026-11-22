from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

admin.site.site_header = "Учебный сайт — администрирование"
admin.site.site_title = "Учебный сайт"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz", lambda r: HttpResponse("ok", content_type="text/plain")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.missions.urls")),
    path("", include("apps.learning.urls")),
    path("", include("apps.rewards.urls")),
    path("parent/", include("apps.parents.urls")),
    path("", include("apps.content.urls")),
    path("", include("apps.ai.urls")),
]
