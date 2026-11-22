from django.http import FileResponse, Http404
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_GET

from apps.accounts.utils import parent_required

from .models import WeeklyReport
from .senders import FakeSender, get_sender
from .weekly import send_weekly_report


def _settings_redirect(child, preview=None):
    url = f"/parent/settings/?child={child.pk}"
    if preview:
        url += f"&preview={preview}"
    return redirect(url)


@parent_required
@require_http_methods(["POST"])
def telegram_settings(request):
    parent = request.parent
    child = get_object_or_404(parent.family.children, pk=request.POST.get("child") or request.GET.get("child") or parent.family.children.first().pk)
    raw = (request.POST.get("telegram_chat_id") or "").strip()
    if raw and not _ok_chat_id(raw):
        messages.error(request, "Chat id — только цифры, для группы можно с минусом в начале.")
        return _settings_redirect(child)
    fmt = request.POST.get("weekly_report_format") or parent.weekly_report_format or "image"
    if fmt not in ("text", "image", "both"):
        fmt = "image"
    parent.telegram_chat_id = raw
    parent.weekly_report_format = fmt
    parent.save(update_fields=["telegram_chat_id", "weekly_report_format"])
    if request.POST.get("send_test"):
        sender = get_sender()
        report = send_weekly_report(child, sender=sender, is_test=True, parent=parent)
        if not raw:
            messages.info(request, "Карточка собрана. Чтобы отправить её в Telegram, укажите chat id.")
        elif isinstance(sender, FakeSender) or not getattr(sender, "token", ""):
            messages.info(request, "Карточка собрана. Чтобы отправить её по-настоящему, нужен токен отдельного бота в TELEGRAM_REPORT_BOT_TOKEN.")
        elif report.notification and report.notification.status == "sent":
            messages.success(request, "Пробный отчёт отправлен в Telegram.")
        else:
            messages.error(request, "Не получилось отправить. Проверьте chat id и токен бота.")
        return _settings_redirect(child, preview=report.pk)
    messages.success(request, "Настройки Telegram сохранены.")
    return _settings_redirect(child)


def _ok_chat_id(value: str) -> bool:
    if value.startswith("-"):
        value = value[1:]
    return value.isdigit() and 3 <= len(value) <= 20


@parent_required
@require_GET
def weekly_image(request, pk):
    report = get_object_or_404(WeeklyReport, pk=pk, child__family=request.parent.family)
    if not report.image:
        raise Http404
    return FileResponse(report.image.open("rb"), content_type="image/png")
