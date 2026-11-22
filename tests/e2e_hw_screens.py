"""Скриншоты «Моя домашка» (iPad 1024×768). Запуск: python tests/e2e_hw_screens.py [base_url] [out_dir].
Данные: seed_demo (+ demo_progress). Тихие часы демо-ребёнка выключаются, ИИ не используется.
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
from apps.ai.models import AISettings  # noqa: E402

kid = ChildProfile.objects.get(user__username="alesya")
kid.settings.quiet_from = kid.settings.quiet_to
kid.settings.save()
AISettings.objects.filter(child=kid).update(enabled=False)
external, errors = [], []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1024, "height": 768}, device_scale_factor=1.5, locale="ru-RU", has_touch=True)
    ctx.set_default_timeout(20000)
    page = ctx.new_page()
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    def shot(name):
        page.screenshot(path=str(OUT / name), full_page=True)
        print("shot", name, flush=True)

    def login_parent():
        page.goto(f"{BASE}/parent/login/")
        page.fill("input[name=username]", "roman")
        page.fill("input[name=password]", "ChildPass123!")
        page.click("button.btn")
        page.wait_for_url("**/parent/")

    login_parent()
    page.click("text=Сделать это устройство семейным")
    page.wait_for_load_state()
    page.click("text=Выход")
    page.wait_for_load_state()
    page.goto(f"{BASE}/start/")
    page.click("text=Алеся")
    for code in ("apple", "cat", "star", "ball"):
        page.click(f"[data-pic={code}]")
    page.wait_for_url("**/home/")
    shot("hw_01_home_tile.png")

    def search(text, subject=""):
        page.goto(f"{BASE}/homework/")
        page.check(f"input[name=subject][value='{subject}']")
        page.fill("input[name=text]", text)
        page.click("form button.btn")
        page.wait_for_load_state()

    page.goto(f"{BASE}/homework/")
    shot("hw_02_empty.png")
    search("дроби с одинаковыми знаменателями", "math")
    shot("hw_03_found_math.png")
    search("тся ться", "ru")
    shot("hw_04_found_ru.png")
    search("слова про еду", "en")
    shot("hw_05_found_en_words.png")
    search("реши 2/7 + 3/7")
    shot("hw_06_task_condition.png")
    search("косинус угла")
    shot("hw_07_unknown_for_dad.png")
    search("сложение дробей", "math")
    page.click(".tile button.btn >> nth=0")
    page.wait_for_url("**/play/**")
    shot("hw_08_practice_started.png")
    page.click("button[aria-label=Выйти]") if page.query_selector("button[aria-label=Выйти]") else page.goto(f"{BASE}/home/")
    ctx.clear_cookies()
    login_parent()
    page.click("text=Домашка")
    page.wait_for_load_state()
    shot("hw_09_parent.png")
    browser.close()

print("external requests:", external)
print("js errors:", errors)
