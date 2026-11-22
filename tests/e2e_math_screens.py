"""Скриншоты полного курса математики 5 кл. (ветка stage2-math).
Запуск: python tests/e2e_math_screens.py [base_url] [out_dir]
Сервер ветки должен быть на :8004, данные — seed_demo.
"""
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8004"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "../screens")
OUT.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402
django.setup()
from apps.accounts.models import ChildProfile  # noqa: E402
from apps.content.models import Exercise  # noqa: E402
from apps.learning.models import Block  # noqa: E402

kid = ChildProfile.objects.get(user__username="alesya")
# Снимки не должны попадать в «тихие часы» демо-ребёнка (вечер Минска).
kid.settings.quiet_from = kid.settings.quiet_to
kid.settings.save()



def blk(key):
    e = Exercise.objects.get(external_key=key)
    return Block.objects.create(
        child=kid, kind="free", title="Практика",
        queue=[{"t": "ex", "id": e.id}], meta={"level": 1},
        subject_code="math",
    ).id


KEYS = {
    "round": "math.nat.rd.ex1",
    "frac": "math.fr.au.ex1",
    "volume": "math.gm.vol.ex1",
    "angle": "math.gm.ang.ex2",
    "power": "math.nat.pw.ex9",
    "ofnum": "math.fr.of.ex2",
}

IDS = {k: blk(v) for k, v in KEYS.items()}

errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(
        viewport={"width": 1024, "height": 768},
        device_scale_factor=1.5, locale="ru-RU", has_touch=True,
    )
    ctx.set_default_timeout(12000)
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    def shot(name):
        path = OUT / name
        page.screenshot(path=str(path), full_page=True)
        print("shot", path, flush=True)

    page.goto(f"{BASE}/parent/login/")
    page.fill("input[name=username]", "roman")
    page.fill("input[name=password]", "ChildPass123!")
    page.click("button.btn")
    page.wait_for_url("**/parent/")
    fam = page.locator("text=Сделать это устройство семейным")
    if fam.count():
        fam.first.click()
        page.wait_for_load_state()
    page.goto(f"{BASE}/start/")
    page.click("text=Алеся")
    page.wait_for_url("**/home/")
    shot("math_01_home.png")

    page.goto(f"{BASE}/map/math/")
    page.wait_for_load_state()
    shot("math_02_map.png")

    page.goto(f"{BASE}/play/{IDS['round']}/")
    page.wait_for_selector("form, .taskform, input")
    shot("math_03_round.png")

    page.goto(f"{BASE}/play/{IDS['frac']}/")
    page.wait_for_selector("input, .taskform")
    # worked example may appear as a prior screen
    if page.locator("text=Разобранный пример").count() or page.locator("text=разобран").count():
        shot("math_04_worked_add_unlike.png")
        nxt = page.locator("button, a").filter(has_text="Дальше")
        if nxt.count():
            nxt.first.click()
            page.wait_for_load_state()
    shot("math_05_add_unlike.png")

    page.goto(f"{BASE}/play/{IDS['volume']}/")
    page.wait_for_selector("input, .taskform")
    shot("math_06_volume.png")

    page.goto(f"{BASE}/play/{IDS['angle']}/")
    page.wait_for_selector(".taskform, button, .opt, [data-choice], form")
    shot("math_07_angle.png")

    page.goto(f"{BASE}/play/{IDS['power']}/")
    page.wait_for_selector("input, .taskform")
    shot("math_08_power.png")

    page.goto(f"{BASE}/play/{IDS['ofnum']}/")
    page.wait_for_selector("input, .taskform")
    shot("math_09_fraction_of_number.png")

    browser.close()

if errors:
    print("JS/page errors:", errors[:8], flush=True)
print("done", flush=True)
