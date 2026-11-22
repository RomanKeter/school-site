"""Русский язык (этап 2, D-200..D-205): типы заданий, контент, интеграция в миссию/карту/SRS."""
import datetime as dt
import json
from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.content.models import Exercise, Skill
from apps.learning.checkers import check
from apps.learning.models import Block
from apps.missions.builder import ensure_mission
from apps.srs.models import ReviewItem

from .test_integration import login_child

BASE = Path(__file__).resolve().parent.parent / "content_samples"


@pytest.fixture
def ru(content):
    for n in ("ru_orthography.json", "ru_grammar.json"):
        call_command("import_content", str(BASE / n), update=True)


def test_fill_letters_checker():
    assert check("fill_letters", {}, {"correct": ["о"]}, {"id": "о"}).correct
    assert not check("fill_letters", {}, {"correct": ["о"]}, {"id": "а"}).correct


def test_punctuation_checker_set_and_hints():
    ans = {"commas": [1, 2]}
    assert check("punctuation", {}, ans, {"commas": [2, 1]}).correct
    r = check("punctuation", {}, ans, {"commas": [1]})
    assert not r.correct and "больше" in r.distractor and r.partial == 0.5
    r = check("punctuation", {}, ans, {"commas": [0, 1, 2]})
    assert not r.correct and "лишняя" in r.distractor
    assert not check("punctuation", {}, ans, {"commas": ["x"]}).correct
    assert not check("punctuation", {}, {"commas": [0]}, {"commas": []}).correct


def test_ru_content_volume_and_shape(ru):
    exs = Exercise.objects.filter(skill__topic__unit__subject__code="ru")
    assert exs.count() >= 40
    skills = Skill.objects.filter(topic__unit__subject__code="ru")
    assert skills.count() == 10
    for s in skills:
        assert s.rule_card and (s.worked_example or {}).get("steps"), s.external_key
    types = set(exs.values_list("type", flat=True))
    assert {"fill_letters", "punctuation", "single_choice", "categorize", "letter_tiles"} <= types
    for ex in exs.filter(type="punctuation"):
        n = len(ex.payload["words"])
        assert all(0 <= c < n - 1 for c in ex.answer["commas"]), ex.external_key
    for ex in exs.filter(type="fill_letters"):
        ids = {o["id"] for o in ex.payload["options"]}
        assert set(ex.answer["correct"]) <= ids and len(ex.payload["parts"]) == 2, ex.external_key


def test_every_ru_exercise_renders_and_hides_answer(client, family, ru):
    _, child = family
    login_child(client, child)
    for ex in Exercise.objects.filter(skill__topic__unit__subject__code="ru"):
        b = Block.objects.create(child=child, kind="free", title="t", queue=[{"t": "ex", "id": ex.id}])
        r = client.get(reverse("play_block", args=[b.id]))
        html = r.content.decode()
        assert r.status_code == 200 and "taskform" in html and "subj-ru" in html, ex.external_key
        assert ex.payload.get("explain", "") not in html, ex.external_key  # пояснение — только после ответа


def test_ru_map_and_home_tile(client, family, ru):
    _, child = family
    login_child(client, child)
    r = client.get(reverse("map", args=["ru"]))
    assert r.status_code == 200
    assert "Безударные гласные" in r.content.decode()
    assert reverse("map", args=["ru"]) in client.get(reverse("home")).content.decode()


def test_tuesday_lesson_is_russian_monday_is_math(family, ru):
    from django.utils import timezone

    from apps.learning.models import DiagnosticResult
    _, child = family
    DiagnosticResult.objects.create(child=child, completed_at=timezone.now())
    tue = ensure_mission(child, dt.date(2026, 3, 3))
    lesson = tue.blocks.get(kind="lesson")
    assert lesson.subject_code == "ru" and lesson.skill.topic.unit.subject.code == "ru"
    mon = ensure_mission(child, dt.date(2026, 3, 9))
    assert mon.blocks.get(kind="lesson").subject_code == "math"


def test_ru_wrong_answer_full_word_explain_and_review_tomorrow(client, family, ru):
    from django.utils import timezone
    _, child = family
    login_child(client, child)
    ex = Exercise.objects.get(external_key="ru.or.un.ex1")
    b = Block.objects.create(child=child, kind="lesson", title="t", skill=ex.skill, subject_code="ru",
                             queue=[{"t": "ex", "id": ex.id}])
    url = reverse("check_exercise", args=[b.id, ex.id])
    html = ""
    for n in (1, 2, 3):
        html = client.post(url, {"answer": json.dumps({"id": "а"}), "attempt_no": n, "hints_used": 0,
                                 "duration_ms": 4000}).content.decode()
    assert "вода" in html and "во́ды" in html and "Повторим завтра" in html
    item = ReviewItem.objects.get(child=child, skill=ex.skill)
    assert item.due_date <= timezone.localdate() + dt.timedelta(days=1)


def test_ru_correct_punctuation_shows_rule(client, family, ru):
    _, child = family
    login_child(client, child)
    ex = Exercise.objects.get(external_key="ru.pu.hg.ex2")
    b = Block.objects.create(child=child, kind="free", title="t", skill=ex.skill, queue=[{"t": "ex", "id": ex.id}])
    html = client.post(reverse("check_exercise", args=[b.id, ex.id]),
                       {"answer": json.dumps({"commas": [1, 2]}), "attempt_no": 1, "hints_used": 0,
                        "duration_ms": 4000}).content.decode()
    assert 'class="fb ok"' in html and "fb-explain" in html


def test_parent_dashboard_lists_russian(client, family, ru):
    parent, _ = family
    client.force_login(parent.user)
    html = client.get("/parent/").content.decode()
    assert "Русский язык" in html and "этап 2" not in html
