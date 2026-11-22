"""Скриншоты офлайн-режима PWA (iPad 1024×768). Запуск: python tests/e2e_pwa_screens.py [base_url] [out_dir]."""
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

kid = ChildProfile.objects.get(user__username="alesya")
kid.settings.quiet_from = kid.settings.quiet_to
kid.settings.save()
external, errors = [], []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1024, "height": 768}, device_scale_factor=1.5, locale="ru-RU", has_touch=True)
    ctx.set_default_timeout(25000)
    page = ctx.new_page()
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") and "chrome-extension" not in r.url else None)
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
    page.click("text=Сделать это устройство семейным")
    page.wait_for_load_state()
    page.click("text=Выход")
    page.goto(f"{BASE}/start/")
    page.click("text=Алеся")
    for code in ("apple", "cat", "star", "ball"):
        page.click(f"[data-pic={code}]")
    page.wait_for_url("**/home/")
    page.wait_for_timeout(800)  # регистрация SW и пакет
    shot("pwa_01_home_online.png")

    ctx.set_offline(True)
    page.wait_for_timeout(300)
    page.reload()
    page.wait_for_timeout(400)
    shot("pwa_02_home_offline.png")

    # серая «Домашка»
    page.evaluate("() => { const a=document.querySelector('a[href*=\"homework\"]'); if(a) a.scrollIntoView(); }")
    shot("pwa_03_needs_net.png")

    ctx.set_offline(False)
    page.wait_for_timeout(400)
    page.reload()
    page.wait_for_selector("text=Разделы", timeout=8000)
    shot("pwa_04_back_online.png")
    browser.close()

print("external requests:", [u for u in external if "google" not in u][:20], "count", len(external))
print("js errors:", errors)
