"""Ручной сквозной сценарий в браузере (Playwright): новый ребёнок → диагностика → миссия дня целиком
(с ошибками, подсказками и разбором) → награды → кабинет родителя → админка.
Запуск: python tests/e2e_walkthrough.py [base_url] [screens_dir]
"""
import re
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "../screens")
SUF = str(int(time.time()) % 1000)
LOGIN = f"kid{SUF}"
NAME = f"Маша{SUF}"
problems, external = [], []
FORBIDDEN = ["Неправильно", "Ошибка", "Неверно", "✗"]


def log(*a):
    print(*a, flush=True)


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1024, "height": 768}, device_scale_factor=1.5, locale="ru-RU", has_touch=True)
    ctx.set_default_timeout(8000)
    page = ctx.new_page()
    page.on("pageerror", lambda e: problems.append(f"JS: {e}"))
    page.on("request", lambda r: external.append(r.url) if not r.url.startswith(BASE) else None)
    page.on("response", lambda r: problems.append(f"HTTP {r.status} {r.url}") if r.status >= 500 else None)

    # 1. Родитель создаёт ребёнка и делает устройство семейным
    page.goto(f"{BASE}/parent/login/")
    page.fill("input[name=username]", "roman"); page.fill("input[name=password]", "ChildPass123!")
    page.click("button.btn"); page.wait_for_url("**/parent/**")
    page.click("text=+ Ребёнок")
    page.fill("input[name=display_name]", NAME); page.fill("input[name=login]", LOGIN)
    page.select_option("select[name=avatar_code]", "owl")
    page.fill("input[name=picture_password]", "moon,fish,star,bike")
    page.click("button:has-text('Создать')"); page.wait_for_url("**/parent/")
    assert "создан" in page.content(), "child not created"
    page.click("text=Сделать это устройство семейным")
    page.click("text=Выход")
    log("1 ok: parent created child + trusted device")

    # 2. Ребёнок входит нажатием аватарки на доверенном устройстве (без картинного пароля)
    page.goto(f"{BASE}/start/")
    page.click(f"text={NAME}")
    page.wait_for_url("**/home/")
    assert "познакомимся" in page.content()
    page.screenshot(path=str(OUT / "10_first_login_diagnostic_home.png"), full_page=True)
    log("2 ok: avatar tap login, diagnostic offered")

    # 3. Проходим всё подряд: диагностика + миссия
    page.click("button:has-text('миссию')")
    steps = 0
    seen_types = set()
    hints_clicked = 0
    shots = {"diag": False, "worked": False, "solution": False, "words": False, "review": False}
    while steps < 120:
        steps += 1
        page.wait_for_load_state()
        url = page.url
        html = page.content()
        txt_main = page.inner_text("main")
        for bad in FORBIDDEN:
            if bad in txt_main:
                problems.append(f"forbidden word '{bad}' at {url}")
        log("  at", steps, url)
        if "/home/" in url:
            if "Миссия выполнена" in html:
                break
            page.click("button:has-text('миссию')")
            continue
        if page.query_selector("#worked"):
            seen_types.add("worked")
            if not shots["worked"]:
                page.screenshot(path=str(OUT / "11_worked_example.png"), full_page=True); shots["worked"] = True
            for _ in range(10):
                if page.is_visible("#worked-go button"):
                    break
                page.click("#worked-more", timeout=3000)
            page.click("#worked-go button", timeout=3000); continue
        if "Ура" in html or "Шаг пройден" in html or "Спасибо" in html or "Миссия выполнена" in html:
            if "Миссия выполнена" in html:
                page.screenshot(path=str(OUT / "13_mission_complete.png"), full_page=True)
            page.click("a.btn:has-text('Дальше')"); continue
        form = page.query_selector("form.taskform")
        if not form:
            problems.append(f"unknown screen {url}"); break
        t = form.get_attribute("data-type")
        seen_types.add(t)
        log("  step", steps, url, t)
        if "Знакомимся" in html and not shots["diag"]:
            page.screenshot(path=str(OUT / "10b_diagnostic_task.png"), full_page=True); shots["diag"] = True
        if "Повторение" in html and not shots["review"]:
            shots["review"] = True

        def submit():
            if page.query_selector("[data-submit-task]"):
                page.click("[data-submit-task]")

        def attempt(i):
            if t in ("single_choice", "fill_blank_choice", "picture_choice", "en_to_ru", "audio_text_choice"):
                opts = page.query_selector_all("[data-choice]:not([disabled])")
                opts[min(i, len(opts) - 1)].click(); return
            if t == "flashcard":
                submit(); return
            if t in ("number_input", "equation", "text_input", "ru_to_en"):
                page.fill("input[name=value]", str(7 + i))
            elif t == "fraction_input":
                page.fill("input[name=num]", "1"); page.fill("input[name=den]", str(3 + i))
            elif t == "step_by_step":
                for inp in page.query_selector_all("input[name=step]"):
                    inp.fill(str(1 + i))
            elif t == "categorize":
                for row in page.query_selector_all(".cat-row"):
                    row.query_selector_all("[data-bucket]")[i % 2].click()
            elif t == "matching":
                lefts = page.query_selector_all("[data-left]")
                rights = page.query_selector_all("[data-right]")
                for k, l in enumerate(lefts):
                    l.click(); rights[(k + i) % len(rights)].click()
            elif t == "drag_order":
                page.query_selector_all("[data-move=down]")[0].click()
            elif t in ("letter_tiles", "tiles"):
                for b in page.query_selector_all("[data-letter]")[:3]:
                    b.click()
            submit()

        for i in range(3):
            with page.expect_response(lambda r: "/check/" in r.url):
                attempt(i)
            page.wait_for_timeout(150)  # htmx swap
            fb = page.query_selector("#feedback .fb")
            if i == 0 and fb.get_attribute("data-final") == "0" and hints_clicked < 3 and page.query_selector("[data-hint-btn]"):
                with page.expect_response(lambda r: "/hint/" in r.url):
                    page.click("[data-hint-btn]")
                page.wait_for_selector("#hint-panel .hint"); hints_clicked += 1
                if hints_clicked == 1:
                    page.screenshot(path=str(OUT / "12_hint_after_mistake.png"), full_page=True)
            if fb.get_attribute("data-final") == "1":
                if "Повторим завтра" in fb.inner_text() and not shots["solution"]:
                    page.screenshot(path=str(OUT / "12b_solution_after_3_tries.png"), full_page=True); shots["solution"] = True
                break
        else:
            problems.append(f"no final feedback after 3 tries: {t} {url}")
        nxt = page.query_selector("#feedback a.next")
        if nxt:
            nxt.click()
        else:
            problems.append(f"no next button {t} {url}"); break
    log(f"3 ok: steps={steps} types={sorted(seen_types)} hints={hints_clicked}")

    # 4. Награды
    page.goto(f"{BASE}/rewards/")
    rewards = page.inner_text("main")
    page.screenshot(path=str(OUT / "14_rewards.png"), full_page=True)
    if "Первый шаг" not in rewards:
        problems.append("badge first_step not awarded")
    m = re.search(r"⭐\s*(\d+)", rewards)
    log("4 rewards stars:", m.group(1) if m else None)

    # 5. Словарик
    page.goto(f"{BASE}/words/")
    words_n = len(page.query_selector_all(".badge"))
    log("5 dictionary words:", words_n)
    page.screenshot(path=str(OUT / "15_dictionary.png"), full_page=True)

    # 6. Родитель видит ребёнка
    page.click("button[aria-label='Выйти']")
    page.goto(f"{BASE}/parent/login/")
    page.fill("input[name=username]", "roman"); page.fill("input[name=password]", "ChildPass123!")
    page.click("button.btn"); page.wait_for_url("**/parent/**")
    page.click(f"text={NAME}")
    ptxt = page.inner_text("main")
    if "выполнена" not in ptxt:
        problems.append("parent does not see mission done")
    page.screenshot(path=str(OUT / "16_parent_new_child.png"), full_page=True)
    page.click("text=Настройки")
    page.click("button:has-text('+15 минут')")
    assert "сохранены" in page.content()
    page.click("text=Выход")
    log("6 ok: parent dashboard + settings")

    # 7. Админка
    page.goto(f"{BASE}/admin/")
    page.fill("input[name=username]", "admin"); page.fill("input[name=password]", "AdminPass123!")
    page.click("input[type=submit]")
    page.goto(f"{BASE}/admin/content/exercise/")
    cnt = page.inner_text("#changelist")
    page.screenshot(path=str(OUT / "17_admin_exercises.png"))
    page.click("#result_list tbody tr:first-child th a")
    page.wait_for_selector("textarea[name=payload]")
    log("7 ok: admin exercise list/edit")
    browser.close()

log("external:", external)
log("PROBLEMS:", problems or "none")
