"""Сквозной прогон + скриншоты ключевых экранов (iPad, 1024×768).
Запуск: python tests/e2e_screens.py [base_url] [out_dir]
Сервер должен быть запущен, данные — seed_demo + demo_progress (+ блоки практики, см. README).
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "../screens")
OUT.mkdir(parents=True, exist_ok=True)
external = []
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1024, "height": 768}, device_scale_factor=1.5, locale="ru-RU", has_touch=True)
    ctx.set_default_timeout(10000)
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
    page.click("text=Сделать это устройство семейным")
    page.wait_for_load_state()
    shot("06_parent_dashboard.png")
    page.click("text=Выход")
    page.wait_for_load_state()

    page.goto(f"{BASE}/start/")
    page.click("text=Алеся")
    for code in ("apple", "cat", "star"):
        page.click(f"[data-pic={code}]")
    shot("01_child_login_pictures.png")
    page.click("[data-pic=ball]")
    page.wait_for_url("**/home/")
    shot("02_home_mission.png")

    page.goto(f"{BASE}/play/1/")
    page.fill("input[name=num]", "5")
    page.fill("input[name=den]", "14")
    page.click("[data-submit-task]")
    page.wait_for_selector(".fb.almost")
    page.click("[data-hint-btn]")
    page.wait_for_selector(".hint .lvl")
    shot("03_exercise_fraction_almost_hint.png")
    page.fill("input[name=den]", "7")
    page.click("[data-submit-task]")
    page.wait_for_selector(".fb.ok")
    shot("03b_exercise_fraction_correct.png")

    page.goto(f"{BASE}/play/2/")
    shot("04_step_by_step_bar_model.png")

    page.goto(f"{BASE}/play/5/")
    shot("05_english_word_card.png")

    page.goto(f"{BASE}/play/4/")
    for i in range(2):
        page.click(f"[data-left=l{i}]")
        page.click(f"[data-right=r{i}]")
    shot("07_matching.png")

    page.goto(f"{BASE}/map/math/")
    shot("08_map_islands.png")

    page.goto(f"{BASE}/play/3/")
    shot("09_categorize.png")
    browser.close()

print("external requests:", external)
print("js errors:", errors)
