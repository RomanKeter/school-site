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
    from apps.content.management.commands.seed_demo import RU_FILES

    for n in RU_FILES:
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
    assert exs.count() >= 600
    skills = Skill.objects.filter(topic__unit__subject__code="ru")
    assert skills.count() >= 50
    assert Skill.objects.filter(topic__unit__subject__code="ru", exercises__isnull=False).distinct().count() == skills.count()
    for s in skills:
        assert s.rule_card and (s.worked_example or {}).get("steps"), s.external_key
    types = set(exs.values_list("type", flat=True))
    assert {"fill_letters", "punctuation", "single_choice", "categorize", "letter_tiles", "morphemes", "dictation", "number_input"} <= types
    for ex in exs.filter(type="morphemes"):
        assert len(ex.answer["labels"]) == len(ex.payload["word"]), ex.external_key
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
        if ex.type == "dictation":
            assert ex.answer["value"] not in html, ex.external_key  # текст диктанта — только в base64 для озвучки


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


def test_morphemes_checker():
    ans = {"labels": "pppkkkksss", "zero": True}
    assert check("morphemes", {}, ans, {"labels": "pppkkkksss", "zero": True}).correct
    r = check("morphemes", {}, ans, {"labels": "pppkkkksss", "zero": False})
    assert not r.correct and "окончание" in r.distractor
    r = check("morphemes", {}, ans, {"labels": "ppkkkkksss", "zero": True})
    assert not r.correct and "приставка" in r.distractor and 0 < r.partial < 1
    assert "Отметь каждую букву" in check("morphemes", {}, ans, {"labels": "ppp", "zero": True}).distractor


def test_dictation_checker():
    ans = {"value": "Яна, иди обедать!"}
    assert check("dictation", {}, ans, {"value": "  яна,  иди обедать! "}).correct
    assert check("dictation", {}, {"value": "Берёза растёт."}, {"value": "береза растет"}).correct  # е = ё, точка не важна
    r = check("dictation", {}, ans, {"value": "Яна иди обедать!"})
    assert not r.correct and "знаки" in r.distractor
    r = check("dictation", {}, ans, {"value": "Яна, иди абедать!"})
    assert not r.correct and "№ 3" in r.distractor
    assert "3" in check("dictation", {}, ans, {"value": "Яна"}).distractor


def test_morphemes_flow_shows_parsed_word(client, family, ru):
    _, child = family
    login_child(client, child)
    ex = Exercise.objects.get(external_key="ru.rp.mo.ex12")  # подоконник
    b = Block.objects.create(child=child, kind="free", title="t", skill=ex.skill, queue=[{"t": "ex", "id": ex.id}])
    url = reverse("check_exercise", args=[b.id, ex.id])
    html = ""
    for n in (1, 2, 3):
        html = client.post(url, {"answer": json.dumps({"labels": "kkkkkkkkkk", "zero": False}), "attempt_no": n,
                                 "hints_used": 0, "duration_ms": 4000}).content.decode()
    assert "под-окон-ник-□" in html and "приставка под" in html


def test_rule_keeper_badge_after_ten_ru_skills(family, ru):
    from apps.learning.models import SkillMastery
    from apps.rewards.badges import evaluate, seed_badges
    from apps.rewards.models import ChildBadge

    seed_badges()
    _, child = family
    skills = list(Skill.objects.filter(topic__unit__subject__code="ru")[:10])
    for s in skills[:9]:
        SkillMastery.objects.create(child=child, skill=s, status="mastered")
    evaluate(child, "skill_mastered", skill=skills[8])
    assert not ChildBadge.objects.filter(child=child, badge__code="rule_keeper").exists()
    SkillMastery.objects.create(child=child, skill=skills[9], status="mastered")
    evaluate(child, "skill_mastered", skill=skills[9])
    assert ChildBadge.objects.filter(child=child, badge__code="rule_keeper").exists()


def test_ru_map_groups_by_units(client, family, ru):
    _, child = family
    login_child(client, child)
    html = client.get(reverse("map", args=["ru"])).content.decode()
    for title in ("Повторение: состав слова и орфограммы", "Фонетика, графика, орфоэпия", "Лексика", "Диктанты"):
        assert f'<h2 class="sea-unit">{title}</h2>' in html
