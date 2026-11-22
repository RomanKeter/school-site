"""Английский язык, полная программа 5 кл. РБ (D-500…D-504): контент и проверка ответов."""
import json
from pathlib import Path

from django.core.management import call_command
from django.urls import reverse

from apps.content.models import Exercise, Skill, Unit, VocabularyWord
from apps.learning.checkers import check
from apps.learning.models import Block

from .test_integration import login_child

BASE = Path(__file__).resolve().parent.parent / "content_samples"

# Навыки полной программы (включая расширенный have got).
PROGRAM_SKILLS = {
    "en.gr.have_got",
    "en.gr.was_were",
    "en.gr.was_were_neg_q",
    "en.gr.past_regular",
    "en.gr.past_irregular",
    "en.gr.past_did",
    "en.gr.past_wh",
    "en.gr.object_pronouns",
    "en.gr.adverbs_freq",
    "en.gr.telling_time",
    "en.gr.countable_some_any",
    "en.gr.much_many",
    "en.gr.should",
    "en.gr.must",
    "en.gr.prepositions",
    "en.gr.articles",
    "en.gr.because",
    "en.gr.future_will",
    "en.gr.plurals_adj",
}

UNIT_KEYS = [f"en.g5.unit{i}" for i in range(1, 10)]


def _correct_given(ex):
    ans = ex.answer or {}
    typ = ex.type
    if typ in ("single_choice", "fill_blank_choice", "audio_text_choice", "fill_letters"):
        return {"id": ans["correct"][0]}
    if typ in ("text_input", "letter_tiles"):
        return {"value": ans.get("value") or (ans.get("accept") or [""])[0]}
    if typ == "matching":
        return {"pairs": dict(ans["pairs"])}
    if typ == "categorize":
        return {"buckets": {k: list(v) for k, v in ans["buckets"].items()}}
    if typ == "drag_order":
        return {"order": list(ans["order"])}
    raise AssertionError(f"unknown type {typ} for {ex.external_key}")


def _wrong_given(ex):
    typ = ex.type
    if typ in ("single_choice", "fill_blank_choice", "audio_text_choice", "fill_letters"):
        ids = [o["id"] for o in (ex.payload.get("options") or [])]
        wrong = next((i for i in ids if i not in {str(c) for c in ex.answer["correct"]}), "zzz")
        return {"id": wrong}
    if typ in ("text_input", "letter_tiles"):
        return {"value": "___wrong___"}
    if typ == "matching":
        pairs = dict(ex.answer["pairs"])
        keys = list(pairs)
        if len(keys) >= 2:
            pairs[keys[0]], pairs[keys[1]] = pairs[keys[1]], pairs[keys[0]]
        return {"pairs": pairs}
    if typ == "categorize":
        buckets = {k: list(v) for k, v in ex.answer["buckets"].items()}
        keys = list(buckets)
        if len(keys) >= 2 and buckets[keys[0]] and buckets[keys[1]]:
            buckets[keys[0]][0], buckets[keys[1]][0] = buckets[keys[1]][0], buckets[keys[0]][0]
        return {"buckets": buckets}
    if typ == "drag_order":
        order = list(ex.answer["order"])
        return {"order": list(reversed(order))}
    raise AssertionError(f"unknown type {typ} for {ex.external_key}")


def test_en_program_json_shape():
    data = json.loads((BASE / "en_program.json").read_text(encoding="utf-8"))
    assert data["format_version"] == 1 and "units" in data
    assert {u["unit"]["key"] for u in data["units"]} >= set(UNIT_KEYS) | {"en.g5.u1"}


def test_en_content_volume_and_shape(content):
    units = Unit.objects.filter(external_key__in=UNIT_KEYS)
    assert units.count() == 9
    words = VocabularyWord.objects.filter(language="en", status="published")
    assert words.count() >= 210
    for w in words:
        assert w.word and w.translation_ru, w.external_key
        assert w.example and w.example_translation, w.external_key
    skills = Skill.objects.filter(external_key__in=PROGRAM_SKILLS)
    assert set(skills.values_list("external_key", flat=True)) == PROGRAM_SKILLS
    for s in skills:
        assert s.rule_card and (s.worked_example or {}).get("steps"), s.external_key
        n = s.exercises.count()
        assert n >= 15, (s.external_key, n)
    exs = Exercise.objects.filter(skill__external_key__in=PROGRAM_SKILLS)
    assert exs.count() >= 19 * 15
    types = set(exs.values_list("type", flat=True))
    assert {"fill_blank_choice", "single_choice", "matching", "text_input",
            "audio_text_choice", "categorize", "drag_order", "letter_tiles"} <= types


def test_every_en_answer_validates(content):
    exs = list(Exercise.objects.filter(skill__external_key__in=PROGRAM_SKILLS))
    assert exs
    for ex in exs:
        ok = check(ex.type, ex.payload, ex.answer, _correct_given(ex))
        assert ok.correct, ex.external_key
        bad = check(ex.type, ex.payload, ex.answer, _wrong_given(ex))
        assert not bad.correct, ex.external_key


def test_every_en_exercise_renders_and_hides_answer(client, family, content):
    _, child = family
    login_child(client, child)
    for ex in Exercise.objects.filter(skill__external_key__in=PROGRAM_SKILLS):
        b = Block.objects.create(child=child, kind="free", title="t", queue=[{"t": "ex", "id": ex.id}])
        r = client.get(reverse("play_block", args=[b.id]))
        html = r.content.decode()
        assert r.status_code == 200 and "taskform" in html, ex.external_key
        # Правильный ответ не должен торчать отдельным полем; сами слова-варианты на экране быть могут.
        if ex.payload.get("explain"):
            assert ex.payload["explain"] not in html, ex.external_key


def test_en_map_lists_units_and_home_tile(client, family, content):
    _, child = family
    login_child(client, child)
    html = client.get(reverse("map", args=["en"])).content.decode()
    assert "was / were" in html
    assert "should / shouldn’t" in html or "should / shouldn" in html
    assert "Future Simple" in html
    assert "must / mustn’t" in html or "must / mustn" in html
    home = client.get(reverse("home")).content.decode()
    assert reverse("map", args=["en"]) in home


def test_en_word_card_has_translation_and_speak(client, family, content):
    _, child = family
    login_child(client, child)
    w = VocabularyWord.objects.get(external_key="en.u1.1.holidays")
    b = Block.objects.create(child=child, kind="words", title="слово", subject_code="en",
                             queue=[{"t": "word", "id": w.id, "mode": "flashcard"}])
    html = client.get(reverse("play_block", args=[b.id])).content.decode()
    assert "holidays" in html and "каникулы" in html
    assert "data-speak" in html
