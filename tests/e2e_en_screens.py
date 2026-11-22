"""Скриншоты английского (полная программа 5 кл.). python tests/e2e_en_screens.py [base_url] [out_dir]"""
import os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8005"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/workspace/school-site/screens")
OUT.mkdir(parents=True, exist_ok=True)
external, errors = [], []

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from apps.accounts.models import ChildProfile
from apps.content.models import Exercise, VocabularyWord
from apps.learning.models import Block

kid = ChildProfile.objects.get(user__username="alesya")


def blk(key=None, word_key=None, mode="flashcard"):
    if word_key:
        w = VocabularyWord.objects.get(external_key=word_key)
        return Block.objects.create(
            child=kid, kind="words", title="Слово", subject_code="en",
            queue=[{"t": "word", "id": w.id, "mode": mode}],
        ).id
    e = Exercise.objects.get(external_key=key)
    return Block.objects.create(
        child=kid, kind="free", title="Практика", subject_code="en",
        queue=[{"t": "ex", "id": e.id}], meta={"level": 1},
    ).id


B = {
    "word": blk(word_key="en.u1.1.holidays"),
    "was": blk("en.gr.ww.ex1"),
    "match": blk("en.gr.op.ex12"),
    "should": blk("en.gr.sh.ex1"),
    "will": blk("en.gr.fu.ex1"),
    "audio": blk("en.gr.ww.ex13"),
    "time": blk("en.gr.tm.ex11"),
}

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1024, "height": 768}, device_scale_factor=1.5,
                              locale="ru-RU", has_touch=True)
    ctx.set_default_timeout(15000)
    page = ctx.new_page()
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(BASE) and not r.url.startswith("data:") else None)
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))

    def shot(name):
        path = OUT / name
        page.screenshot(path=str(path), full_page=True)
        print("shot", path, flush=True)

    page.goto(f"{BASE}/parent/login/")
    page.fill("input[name=username]", "roman")
    page.fill("input[name=password]", "ChildPass123!")
    page.click("button.btn")
    page.wait_for_url("**/parent/**")
    if page.get_by_text("Сделать это устройство семейным").count():
        page.click("text=Сделать это устройство семейным")
        page.wait_for_load_state()
    page.goto(f"{BASE}/start/")
    page.click("text=Алеся")
    page.wait_for_url("**/home/")
    shot("en_01_home_tile.png")

    page.goto(f"{BASE}/map/en/")
    page.wait_for_load_state()
    shot("en_02_map_islands.png")

    page.goto(f"{BASE}/play/{B['word']}/")
    page.wait_for_selector(".wordcard, .w")
    shot("en_03_word_holidays.png")

    page.goto(f"{BASE}/play/{B['was']}/")
    page.wait_for_selector(".taskform")
    shot("en_04_was_were.png")
    # выбрать правильный was и снять верный ответ
    page.click(".opt", force=True)  # may be wrong; better click by text
    # re-open and click the correct option "was"
    page.goto(f"{BASE}/play/{B['was']}/")
    page.wait_for_selector(".taskform")
    page.get_by_role("button", name="was", exact=True).click()
    page.wait_for_selector(".fb.ok, .fb")
    shot("en_05_was_were_correct.png")

    page.goto(f"{BASE}/play/{B['should']}/")
    page.wait_for_selector(".taskform")
    shot("en_06_should.png")

    page.goto(f"{BASE}/play/{B['will']}/")
    page.wait_for_selector(".taskform")
    shot("en_07_future_will.png")

    page.goto(f"{BASE}/play/{B['match']}/")
    page.wait_for_selector("[data-left], .taskform")
    shot("en_08_object_pronouns_match.png")

    page.goto(f"{BASE}/play/{B['audio']}/")
    page.wait_for_selector(".speak, .taskform")
    shot("en_09_audio_choice.png")

    page.goto(f"{BASE}/play/{B['time']}/")
    page.wait_for_selector(".taskform")
    shot("en_10_telling_time.png")

    browser.close()

print("external requests:", external)
print("js errors:", errors)
