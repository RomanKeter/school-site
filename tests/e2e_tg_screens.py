"""Скриншоты недельного отчёта в Telegram (iPad 1024×768). Запуск: python tests/e2e_tg_screens.py [base_url] [out_dir].
Данные: seed_demo (+ demo_progress). Тихие часы демо-ребёнка выключаются.
"""
import os
import sys
from pathlib import Path

import django
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8003"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "../screens")
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from apps.accounts.models import ChildProfile  # noqa: E402
from apps.reports.models import WeeklyReport  # noqa: E402

kid = ChildProfile.objects.get(user__username="alesya")
kid.settings.quiet_from = kid.settings.quiet_to
kid.settings.save()
external, errors = [], []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1024, "height": 768}, device_scale_factor=1.5, locale="ru-RU", has_touch=True)
    ctx.set_default_timeout(30000)
    page = ctx.new_page()
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    def shot(name):
        page.screenshot(path=str(OUT / name), full_page=True)
        print("shot", name, flush=True)

    page.goto(f"{BASE}/parent/login/")
    page.fill("input[name=username]", "roman")
    page.fill("input[name=password]", "ChildPass123!")
    page.click("button.btn")
    page.wait_for_url("**/parent/")
    page.click("text=Настройки")
    page.wait_for_load_state()
    shot("tg_01_settings.png")

    page.fill("input[name=telegram_chat_id]", "123456789")
    page.select_option("select[name=weekly_report_format]", "image")
    page.click("button[name=send_test]")
    page.wait_for_url("**/parent/settings/**")
    page.wait_for_selector("img[alt=\"Недельный отчёт\"]")
    shot("tg_02_test_preview.png")
    browser.close()

# Полная карточка 1080×1350 — тот же файл, что уходит в Telegram
rep = WeeklyReport.objects.filter(child=kid).order_by("-id").first()
if not rep or not rep.image:
    raise SystemExit("нет карточки после пробной отправки")
dest = OUT / "tg_03_weekly_card.png"
dest.write_bytes(rep.image.read())
print("shot", dest.name, flush=True)

print("external requests:", external)
print("js errors:", errors)
