"""Офлайн-пакет, синхронизация, манифест и service worker (раздел 23.5)."""
import json

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.utils import child_required

from . import offline


@child_required
@require_GET
def package(request):
    pkg = offline.build_package(request.child)
    offline.mark_downloaded(request.child)
    return JsonResponse(pkg)


@child_required
@require_POST
def sync(request):
    try:
        payload = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "не JSON"}, status=400)
    items = payload.get("items") or []
    if not isinstance(items, list):
        return JsonResponse({"ok": False, "error": "items — список"}, status=400)
    return JsonResponse(offline.sync_batch(request.child, items))


@require_GET
def manifest(request):
    icon = "/static/favicon.svg"
    data = {
        "name": "Учимся с Масей",
        "short_name": "Мася",
        "start_url": "/home/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#F5F1EA",
        "theme_color": "#4C6A85",
        "lang": "ru",
        "icons": [
            {"src": icon, "sizes": "any", "type": "image/svg+xml", "purpose": "any"},
            {"src": "/static/img/mascot/zubrik-hello-face.svg", "sizes": "any", "type": "image/svg+xml"},
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


@require_GET
def service_worker(request):
    path = settings.BASE_DIR / "static" / "js" / "sw.js"
    resp = FileResponse(path.open("rb"), content_type="application/javascript")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp
