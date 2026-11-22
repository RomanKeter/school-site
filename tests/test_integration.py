import json
import datetime as dt

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.services import create_child, create_parent
from apps.content.models import Exercise, Skill
from apps.learning.models import Block
from apps.missions.builder import ensure_mission
from apps.rewards.models import StarTransaction
from apps.rewards.stars import award, DAILY_CAP
from apps.srs.models import ReviewItem


def login_child(client, child, seq=("apple", "cat", "star", "ball")):
    from apps.accounts.utils import set_trusted_device
    from django.http import HttpResponse

    resp = set_trusted_device(HttpResponse(), child.family)
    client.cookies["family_device"] = resp.cookies["family_device"].value
    return client.post(reverse("child_pictures", args=[child.pk]), {"sequence": ",".join(seq)})


def test_picture_login_and_lockout(client, family):
    _, child = family
    for _ in range(5):
        r = login_child(client, child, ("moon", "moon", "moon", "moon"))
        assert "ошибка" not in r.content.decode().lower()
    r = login_child(client, child)  # заблокировано на 5 минут
    assert "передохнём" in r.content.decode()


def test_picture_login_ok(client, family):
    _, child = family
    r = login_child(client, child)
    assert r.status_code == 302 and r.url == reverse("home")


def test_idor_parent_cannot_see_other_family(client, family):
    p2 = create_parent("parent2", "VeryLongPass456", family_name="Семья Б")
    _, child_a = family
    client.force_login(p2.user)
    assert client.get(f"/parent/?child={child_a.pk}").status_code == 404
    assert client.get(f"/parent/settings/?child={child_a.pk}").status_code == 404


def test_child_cannot_open_parent_pages(client, family):
    _, child = family
    login_child(client, child)
    assert client.get("/parent/").status_code == 404


def test_child_cannot_play_foreign_block(client, family, content):
    parent, child = family
    other = create_child(parent.family, "kid2", "Миша", ["fish"] * 4)
    m = ensure_mission(other)
    b = m.blocks.first()
    login_child(client, child)
    assert client.get(reverse("play_block", args=[b.id])).status_code == 404


def test_import_dry_run_writes_nothing(db, tmp_path):
    from apps.content.models import Unit

    data = {"format_version": 1, "subject": "math", "unit": {"key": "u.x", "title": "X"},
            "topics": [{"key": "t.x", "title": "T", "skills": [{"key": "s.x", "title": "S", "exercises": [
                {"key": "e.x", "type": "number_input", "payload": {"prompt": "1+1"}, "answer": {"value": "2"}}]}]}]}
    f = tmp_path / "c.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    call_command("import_content", str(f), dry_run=True)
    assert not Unit.objects.filter(external_key="u.x").exists()
    call_command("import_content", str(f))
    assert Exercise.objects.filter(external_key="e.x").exists()
    with pytest.raises(Exception):
        call_command("import_content", str(f))  # дубликат без --update
    call_command("import_content", str(f), update=True)


def test_import_reports_missing_fields(db, tmp_path):
    data = {"format_version": 1, "subject": "math", "unit": {"key": "u.y", "title": "Y"},
            "topics": [{"key": "t.y", "title": "T", "skills": [{"key": "s.y", "title": "S",
                                                                "exercises": [{"key": "e.y", "payload": {}}]}]}]}
    f = tmp_path / "c.json"
    f.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(Exception):
        call_command("import_content", str(f))
    from apps.content.models import Unit
    assert not Unit.objects.filter(external_key="u.y").exists()  # всё или ничего


def test_seed_content_volume(content):
    math = Exercise.objects.filter(skill__topic__unit__subject__code="math").count()
    assert math >= 30
    from apps.content.models import VocabularyWord
    assert VocabularyWord.objects.count() >= 40


def test_star_dedupe_and_cap(family):
    _, child = family
    today = dt.date(2026, 3, 3)
    assert award(child, 2, "attempt", 1, today) == 2
    assert award(child, 2, "attempt", 1, today) == 0  # повторная отправка
    for i in range(2, 100):
        award(child, 2, "attempt", i, today)
    assert sum(t.amount for t in StarTransaction.objects.filter(child=child, day=today)) == DAILY_CAP
    assert award(child, 10, "mission", 1, today) == 10  # бонус вне потолка


def test_first_mission_starts_with_diagnostic(family, content):
    _, child = family
    m = ensure_mission(child, dt.date(2026, 3, 2))
    kinds = list(m.blocks.values_list("kind", flat=True))
    assert kinds == ["diagnostic"]


def test_regular_mission_structure_and_interleaved_review(family, content):
    from apps.learning.models import DiagnosticResult
    from apps.srs.services import ensure_item
    from django.utils import timezone
    from apps.content.models import VocabularyWord

    _, child = family
    DiagnosticResult.objects.create(child=child, completed_at=timezone.now())
    day0 = dt.date(2026, 3, 1)
    skills = list(Skill.objects.filter(topic__unit__subject__code="math"))[:3]
    for s in skills:
        ensure_item(child, today=day0, skill=s)
    for w in VocabularyWord.objects.all()[:4]:
        ensure_item(child, today=day0, word=w)
    m = ensure_mission(child, dt.date(2026, 3, 2))  # понедельник
    kinds = list(m.blocks.values_list("kind", flat=True))
    assert kinds[0] == "warmup" and "review" in kinds and "lesson" in kinds and "words" in kinds
    assert kinds[-1] == "surprise"
    review = m.blocks.get(kind="review")
    items = [ReviewItem.objects.get(pk=s["item"]) for s in review.queue]
    from apps.srs.interleave import max_run
    assert max_run(items, key=lambda it: it.group_key()) == 1
    words = m.blocks.get(kind="words")
    assert len({s["id"] for s in words.queue}) == 5  # 5 новых слов


def test_answer_flow_wrong_then_solution_goes_to_review_tomorrow(client, family, content):
    from apps.learning.models import DiagnosticResult
    from django.utils import timezone
    _, child = family
    DiagnosticResult.objects.create(child=child, completed_at=timezone.now())
    login_child(client, child)
    m = ensure_mission(child)
    lesson = m.blocks.get(kind="lesson")
    ex = Exercise.objects.filter(skill=lesson.skill, type="single_choice").first()
    lesson.queue = [{"t": "ex", "id": ex.id}]
    lesson.save()
    url = reverse("check_exercise", args=[lesson.id, ex.id])
    wrong = next(o["id"] for o in ex.payload["options"] if o["id"] not in ex.answer["correct"])
    html = ""
    for n in (1, 2, 3):
        r = client.post(url, {"answer": json.dumps({"id": wrong}), "attempt_no": n, "hints_used": 0, "duration_ms": 5000})
        html = r.content.decode()
        for bad in ("Неправильно", "Ошибка", "Неверно", "✗"):
            assert bad not in html
    assert "Повторим завтра" in html
    item = ReviewItem.objects.get(child=child, skill=lesson.skill)
    assert item.due_date <= timezone.localdate() + dt.timedelta(days=1)
    assert StarTransaction.objects.filter(child=child, source_type="attempt").count() == 1  # «за упорство»
    # повторная отправка того же задания не начисляет звёзды второй раз
    client.post(url, {"answer": json.dumps({"id": ex.answer["correct"][0]}), "attempt_no": 1, "hints_used": 0, "duration_ms": 100})
    assert StarTransaction.objects.filter(child=child, source_type="attempt").count() == 1


def test_correct_answer_not_in_html_before_answer(client, family, content):
    from apps.learning.models import DiagnosticResult
    from django.utils import timezone
    _, child = family
    DiagnosticResult.objects.create(child=child, completed_at=timezone.now())
    login_child(client, child)
    ex = Exercise.objects.get(external_key="math.div.s3.ex1")  # НОД(24,36)=12
    b = Block.objects.create(child=child, kind="free", title="t", queue=[{"t": "ex", "id": ex.id}])
    html = client.get(reverse("play_block", args=[b.id])).content.decode()
    assert "НОД(24, 36)" in html
    assert '"value": "12"' not in html and "solution" not in html.lower().replace("data-solution", "")


def test_quiet_hours_and_limit(client, family, content):
    import datetime as _dt
    _, child = family
    login_child(client, child)
    s = child.settings
    s.quiet_from, s.quiet_to = _dt.time(0, 0), _dt.time(23, 59, 59)
    s.save()
    assert "время отдыха" in client.get(reverse("home")).content.decode()
    s.quiet_from, s.quiet_to = _dt.time(23, 59, 59), _dt.time(0, 0, 1)
    s.save()
    from apps.learning.services import activity_get
    from apps.accounts.utils import local_today
    a = activity_get(child, local_today(child.family))
    a.active_seconds = 31 * 60
    a.save()
    assert "На сегодня всё" in client.get(reverse("home")).content.decode()


def test_streak_with_freeze(family):
    from apps.rewards.streaks import on_mission_done
    _, child = family
    d = dt.date(2026, 3, 3)  # вторник
    on_mission_done(child, d)
    s, _ = on_mission_done(child, d + dt.timedelta(days=1))
    assert s.current == 2
    s, _ = on_mission_done(child, d + dt.timedelta(days=3))  # пропуск 1 дня → заморозка
    assert s.current == 3 and s.freezes_available == 0
    s, comeback = on_mission_done(child, d + dt.timedelta(days=8))
    assert s.current == 1 and s.best == 3 and comeback


def test_adaptive_in_block_three_right_raise_two_wrong_lower(client, family, content):
    """Подстройка сложности через реальные ответы; слово «понижен» ребёнку не показывается."""
    _, child = family
    login_child(client, child)
    skill = Skill.objects.get(external_key="math.div.signs_2_5_10")
    b = Block.objects.create(child=child, kind="lesson", title="t", skill=skill,
                             queue=[{"t": "adaptive", "skill": skill.id, "stage": "solo"} for _ in range(8)],
                             meta={"level": 1})
    seen = []

    def answer(correct):
        client.get(reverse("play_block", args=[b.id]))
        b.refresh_from_db()
        ex = Exercise.objects.get(pk=b.queue[b.position]["chosen"])
        seen.append(ex.difficulty)
        given = _answer_for(ex, correct)
        html = ""
        for n in ((1,) if correct else (1, 2, 3)):
            html = client.post(reverse("check_exercise", args=[b.id, ex.id]),
                               {"answer": json.dumps(given), "attempt_no": n, "hints_used": 0, "duration_ms": 3000}).content.decode()
        assert "пониж" not in html.lower() and "уровень" not in html.lower()
        b.refresh_from_db()

    for _ in range(3):
        answer(True)
    assert b.meta["level"] == 2
    answer(False)
    answer(False)
    assert b.meta["level"] == 1
    assert seen[3] == 2  # после 3 верных подряд пришло задание сложнее


def _answer_for(ex, correct):
    a = ex.answer
    t = ex.type
    if t in ("single_choice", "fill_blank_choice"):
        ids = [o["id"] for o in ex.payload["options"]]
        return {"id": a["correct"][0] if correct else next(i for i in ids if i not in a["correct"])}
    if t in ("number_input", "equation"):
        return {"value": a["value"] if correct else "999999"}
    if t == "fraction_input":
        n, d = a["value"].split("/")
        return {"num": n, "den": d} if correct else {"num": "0", "den": "1"}
    if t == "categorize":
        return {"buckets": a["buckets"]} if correct else {"buckets": {}}
    if t == "step_by_step":
        return {"steps": [str(s["answer"]) for s in a["steps"]]} if correct else {"steps": []}
    if t == "drag_order":
        return {"order": a["order"]} if correct else {"order": []}
    if t == "matching":
        return {"pairs": a["pairs"]} if correct else {"pairs": {}}
    return {"value": a.get("value", "") if correct else "zzz"}


def test_diagnostic_completion_appends_regular_mission(client, family, content):
    """Диагностика заканчивается словами → результат сохранён и в миссию добавлены обычные шаги."""
    from apps.learning.models import DiagnosticResult
    _, child = family
    login_child(client, child)
    m = ensure_mission(child)
    diag = m.blocks.get(kind="diagnostic")
    for _ in range(len(diag.queue)):
        diag.refresh_from_db()
        step = diag.queue[diag.position]
        if step["t"] == "ex":
            ex = Exercise.objects.get(pk=step["id"])
            r = client.post(reverse("check_exercise", args=[diag.id, ex.id]),
                            {"answer": json.dumps(_answer_for(ex, True)), "attempt_no": 1, "hints_used": 0, "duration_ms": 4000})
        else:
            r = client.post(reverse("check_word", args=[diag.id, step["id"]]),
                            {"answer": json.dumps({"id": step["id"]}), "mode": step["mode"], "attempt_no": 1})
        html = r.content.decode()
        assert "Записал" in html and "Точно" not in html  # нейтрально, без оценки
    diag.refresh_from_db()
    assert diag.status == "done"
    assert DiagnosticResult.objects.get(child=child).completed_at
    kinds = list(m.blocks.order_by("order").values_list("kind", flat=True))
    assert kinds[0] == "diagnostic" and "lesson" in kinds and kinds[-1] == "surprise"
    m.refresh_from_db()
    assert m.status != "done"
    # освоенные на диагностике навыки отмечены как знакомые
    from apps.learning.models import SkillMastery
    assert SkillMastery.objects.filter(child=child, placed=True).exists()
    # знакомые слова стартуют сразу с интервала 3 дня
    assert ReviewItem.objects.filter(child=child, item_type="word", interval_days=3).exists()
