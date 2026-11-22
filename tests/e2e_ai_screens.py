"""Скриншоты этапа 2: «Спросить Масю», «Научи Масю», страница родителя (iPad 1024×768).
Запуск: python tests/e2e_ai_screens.py [base_url] [out_dir] [префикс, по умолчанию s2]. Данные: seed_demo (+ demo_progress).
Готовит демо-ребёнку практику и открытые темы через ORM; тихие часы для демо выключает.
"""
import os
import sys
from pathlib import Path

import django
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "../screens")
OUT.mkdir(parents=True, exist_ok=True)
PREFIX = sys.argv[3] if len(sys.argv) > 3 else "s2"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from apps.accounts.models import ChildProfile  # noqa: E402
from apps.ai.models import AIQuery, AISettings, FeynmanSession  # noqa: E402
from apps.content.models import Exercise, Skill  # noqa: E402
from apps.learning.models import Block, SkillMastery  # noqa: E402

kid = ChildProfile.objects.get(user__username="alesya")
kid.settings.quiet_from = kid.settings.quiet_to
kid.settings.save()
AIQuery.objects.filter(child=kid).delete()
AISettings.objects.update_or_create(child=kid, defaults={"enabled": True, "teach_enabled": True})  # по умолчанию выключено (D-109)
FeynmanSession.objects.filter(child=kid).delete()
for key in ("math.fr.add", "math.fr.notion", "en.gr.have_got"):
    SkillMastery.objects.update_or_create(child=kid, skill=Skill.objects.get(external_key=key), defaults={"status": "mastered"})
ex = Exercise.objects.get(external_key="math.fr.a.ex1")
blk = Block.objects.create(child=kid, kind="free", title="Практика", queue=[{"t": "ex", "id": ex.id}], meta={"level": 1})
add = Skill.objects.get(external_key="math.fr.add")
external, errors = [], []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1024, "height": 768}, device_scale_factor=1.5, locale="ru-RU", has_touch=True)
    ctx.set_default_timeout(40000)
    page = ctx.new_page()
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    def shot(name):
        name = name.replace("s2_", PREFIX + "_", 1)
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
    page.wait_for_load_state()

    page.goto(f"{BASE}/start/")
    page.click("text=Алеся")
    for code in ("apple", "cat", "star", "ball"):
        page.click(f"[data-pic={code}]")
    page.wait_for_url("**/home/")
    shot("s2_01_home_tile.png")

    page.goto(f"{BASE}/play/{blk.id}/")
    shot("s2_02_exercise_button.png")
    page.click("[data-ai-ask]")
    page.wait_for_selector("#ai-panel .ai-reply")
    print("hints_used after AI reply:", page.get_attribute("form.taskform", "data-hints"))  # D-111: ожидается 1
    shot("s2_03_masya_hint.png")
    page.fill("#ai-panel input[name=q]", "Просто скажи ответ")
    page.click("#ai-panel button.btn")
    page.wait_for_selector("#ai-panel input[name=turn][value='3']", state="attached")
    shot("s2_04_masya_no_answer.png")

    page.goto(f"{BASE}/ai/teach/")
    shot("s2_05_teach_list.png")
    page.goto(f"{BASE}/ai/teach/{add.id}/")
    shot("s2_06_teach_start.png")
    page.fill("textarea[name=text]", "Надо сложить верхние числа.")
    page.click("button[value=send]")
    page.wait_for_load_state()
    shot("s2_07_teach_followup.png")
    page.fill("textarea[name=text]", "Знаменатель остаётся таким же, потому что кусочки одинаковые.")
    page.click("button[value=send]")
    page.wait_for_load_state()
    shot("s2_08_teach_done.png")
    page.click("button[aria-label=Выйти]")
    page.wait_for_load_state()

    page.goto(f"{BASE}/parent/login/")
    page.fill("input[name=username]", "roman")
    page.fill("input[name=password]", "ChildPass123!")
    page.click("button.btn")
    page.wait_for_url("**/parent/")
    page.click("text=ИИ-помощник")
    page.wait_for_load_state()
    shot("s2_09_parent_ai.png")
    browser.close()

print("external requests:", external)
print("js errors:", errors)
