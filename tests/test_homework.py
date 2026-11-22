"""Этап 2: «Моя домашка» (раздел 5.8 ТЗ, D-300…D-307). Сеть не используется."""
import datetime as dt

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.ai.models import AIQuery, AISettings
from apps.ai.providers import FakeProvider, set_provider_for_tests
from apps.content.models import Exercise, Skill, Topic
from apps.homework import matching, services
from apps.homework.models import ContentRequest, HomeworkRequest
from apps.learning.models import AssignedSkill, Attempt, Block
from apps.missions.builder import ensure_mission
from tests.test_integration import login_child


@pytest.fixture(autouse=True)
def _offline_ai(settings):
    settings.AI = {**settings.AI, "PROVIDER": "fake", "GEMINI_API_KEY": "", "OPENROUTER_API_KEY": "", "MIN_INTERVAL_SECONDS": 0}
    set_provider_for_tests(None)
    yield
    set_provider_for_tests(None)


@pytest.fixture
def hw(content, family):
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent / "content_samples"
    for n in ("ru_orthography.json", "ru_grammar.json"):
        call_command("import_content", str(base / n), update=True)
    call_command("seed_homework")
    return family[1]


def _key(m):
    return Skill.objects.get(pk=m["id"]).external_key if m["kind"] == "skill" else "T:" + Topic.objects.get(pk=m["id"]).external_key


# 44 формулировки: 22 — по ним настраивался поиск, 22 — отложенные (написаны после настройки). AC-2-04: ≥ 85 %.
PHRASES = [
    ("дроби с одинаковыми знаменателями", "math.fr.add"), ("сложение дробей", "math.fr.add"), ("вычитание дробей", "math.fr.add"),
    ("слажение дробей", "math.fr.add"), ("сравнить дроби", "math.fr.compare"), ("что такое дробь", "math.fr.notion"),
    ("числитель и знаменатель", "math.fr.notion"), ("признаки делимости на 3 и 9", "math.div.signs_3_9"),
    ("делимость на 5", "math.div.signs_2_5_10"), ("признаки делимасти на 2", "math.div.signs_2_5_10"),
    ("НОД", "math.div.gcd"), ("наибольший общий делитиль", "math.div.gcd"), ("простые числа", "math.primes.notion"),
    ("разложить на простые множители", "math.primes.notion"), ("уравнения", "math.eq.simple"),
    ("решать уравнения", "math.eq.simple"), ("параграф 18", "math.fr.add|math.fr.notion|math.fr.compare"),
    ("have got has got", "en.gr.have_got"), ("слова про еду", "T:en.food"), ("animals", "T:en.animals"),
    ("выучить слова семья", "T:en.family"), ("дни недели", "T:en.weather"),
    # отложенные
    ("складывать дроби", "math.fr.add"), ("дроби вычитать", "math.fr.add"), ("дробей сравнение", "math.fr.compare"),
    ("какая дробь больше", "math.fr.compare"), ("доли и дроби", "math.fr.notion"),
    ("знаминатель", "math.fr.notion|math.fr.add|math.fr.compare"), ("делится ли число на 9", "math.div.signs_3_9"),
    ("признак делимости на десять", "math.div.signs_2_5_10"), ("чётные числа", "math.div.signs_2_5_10"),
    ("общий делитель двух чисел", "math.div.gcd"), ("составные числа", "math.primes.notion"),
    ("простые и составные", "math.primes.notion"), ("уравнение с иксом", "math.eq.simple"),
    ("задачи на движение", "math.eq.simple"), ("has got", "en.gr.have_got"), ("животные англ", "T:en.animals"),
    ("words about school", "T:en.school"), ("my family слова", "T:en.family"), ("фрукты", "T:en.food"),
    ("комнаты в доме", "T:en.home"), ("времена года", "T:en.weather"), ("простые числа до 100", "math.primes.notion"),
    # русский язык (после слияния stage2-ru)
    ("тся ться", "ru.or.tsya"), ("безударные гласные", "ru.or.unstressed"), ("слова с чередованием", "ru.or.alt"),
    ("приставки на з с", "ru.or.zs"), ("разделительный твёрдый знак", "ru.or.signs"), ("не с глаголами", "ru.or.ne"),
    ("части речи", "ru.mo.pos"), ("запятые при однородных", "ru.pu.homog"), ("обращение запятые", "ru.pu.address"),
    ("словарные слова", "ru.or.vocab"), ("одноротные члены", "ru.pu.homog"),
]


def test_search_accuracy_ac_2_04(hw):
    ok, bad = 0, []
    for text, exp in PHRASES:
        res = matching.search(text)
        if res and _key(res[0]) in exp.split("|"):
            ok += 1
        else:
            bad.append(text)
    assert ok / len(PHRASES) >= 0.85, bad


def test_search_subject_filter_and_nothing_found(hw):
    assert all(m["subject"] == "en" for m in matching.search("дроби", "en")) and not matching.search("дроби", "en")
    assert matching.search("дроби", "math")
    assert matching.search("косинус угла") == []
    assert _key(matching.search("тся ться", "ru")[0]) == "ru.or.tsya"


def test_looks_like_task():
    assert matching.looks_like_task("реши 2/7 + 3/7")
    assert matching.looks_like_task("x + 37 = 105")
    assert matching.looks_like_task("Найди НОД чисел 24 и 36")
    assert not matching.looks_like_task("§ 18 упр. 145")
    assert not matching.looks_like_task("дроби с одинаковыми знаменателями")


def test_submit_found_task_and_unknown(hw):
    child = hw
    req, msg = services.submit(child, "дроби с одинаковыми знаменателями", "math")
    assert req.match_method == "match" and req.matches and msg == ""
    req, msg = services.submit(child, "реши 2/7 + 3/7", "")
    assert req.looks_like_task and msg == services.MSG_TASK and _key(req.matches[0]) == "math.fr.add"  # тему нашли, задачу не решаем
    req, msg = services.submit(child, "косинус угла", "")
    assert req.match_method == "none" and msg == services.MSG_UNKNOWN
    assert ContentRequest.objects.get().text == "косинус угла"
    services.submit(child, "косинус угла", "")
    assert ContentRequest.objects.count() == 1  # повтор не плодит заявки


def test_submit_masks_pii_and_refuses_unsafe(hw):
    req, _ = services.submit(hw, "меня зовут Яна, дроби", "")
    assert "Яна" not in req.text
    req, msg = services.submit(hw, "расскажи страшилку", "")
    assert req is None and "школьными темами" in msg and not HomeworkRequest.objects.filter(text__contains="страшил").exists()


def test_ai_classifier_only_when_enabled(hw):
    child = hw
    fake = FakeProvider(replies=['{"topic_ids": ["s%d"], "confidence": 0.8}' % Skill.objects.get(external_key="math.eq.simple").id])
    fake.offline = False
    set_provider_for_tests(fake)
    req, _ = services.submit(child, "абракадабра непонятная", "")
    assert req.match_method == "none" and not fake.calls  # ИИ выключен родителем (D-109)
    AISettings.objects.create(child=child, enabled=True)
    req, msg = services.submit(child, "абракадабра непонятная", "")
    assert req.match_method == "ai" and _key(req.matches[0]) == "math.eq.simple" and msg == ""
    sent = fake.calls[0][1]["content"]
    assert "абракадабра" in sent and "Простые уравнения" in sent
    assert AIQuery.objects.get(kind="homework").units == 0


def test_ai_classifier_low_confidence_goes_to_parent(hw):
    child = hw
    AISettings.objects.create(child=child, enabled=True)
    fake = FakeProvider(replies=['{"topic_ids": [], "confidence": 0.3}'])
    fake.offline = False
    set_provider_for_tests(fake)
    req, msg = services.submit(child, "абракадабра", "")
    assert req.match_method == "none" and msg == services.MSG_UNKNOWN and ContentRequest.objects.count() == 1
    assert "low_confidence" in AIQuery.objects.get().flags


def test_practice_known_first_and_mission(hw):
    child = hw
    skill = Skill.objects.get(external_key="math.fr.add")
    exs = list(Exercise.objects.filter(skill=skill).order_by("difficulty", "id"))
    Attempt.objects.create(child=child, exercise=exs[-1], is_correct=True, is_final=True)
    req, _ = services.submit(child, "сложение дробей", "math")
    today = dt.date(2026, 11, 22)
    block = services.start_practice(req, "skill", skill.id, today)
    assert 5 <= len(block.queue) <= 8 and block.queue[0]["id"] == exs[-1].id  # сначала знакомое
    assert AssignedSkill.objects.get(child=child, skill=skill).date == today  # миссия ещё не собрана → сегодня
    ensure_mission(child, today)
    req2, _ = services.submit(child, "уравнения", "math")
    eq = Skill.objects.get(external_key="math.eq.simple")
    services.start_practice(req2, "skill", eq.id, today)
    assert AssignedSkill.objects.get(child=child, skill=eq).date == today + dt.timedelta(days=1)
    assert services.start_practice(req2, "skill", skill.id, today) is None  # только из найденного


def test_words_practice(hw):
    child = hw
    req, _ = services.submit(child, "слова про еду", "en")
    topic = Topic.objects.get(external_key="en.food")
    block = services.start_practice(req, "words", topic.id, dt.date(2026, 11, 22))
    assert block.kind == "words" and len(block.queue) == 8 and block.queue[0]["mode"] == "flashcard"


def test_views_child_flow_and_parent(client, hw):
    child = hw
    login_child(client, child)
    assert "Что задали?" in client.get(reverse("home")).content.decode()
    r = client.post(reverse("homework"), {"text": "сложение дробей", "subject": "math"})
    body = r.content.decode()
    assert "Тренироваться" in body and "Сложение и вычитание дробей" in body
    req = HomeworkRequest.objects.get()
    skill = Skill.objects.get(external_key="math.fr.add")
    r = client.post(reverse("homework_start", args=[req.id]), {"kind": "skill", "id": skill.id})
    blk = Block.objects.get(meta__homework=req.id)
    assert r.status_code == 302 and r.url == reverse("play_block", args=[blk.id])
    assert client.get(r.url).status_code == 200
    body = client.post(reverse("homework"), {"text": "косинус угла"}).content.decode()
    assert services.MSG_UNKNOWN in body
    assert client.get(reverse("parent_homework")).status_code == 404  # ребёнку нельзя
    client.force_login(child.family.parents.first().user)
    page = client.get(reverse("parent_homework")).content.decode()
    assert "косинус угла" in page and "сложение дробей" in page
    cr = ContentRequest.objects.get()
    client.post(reverse("parent_homework"), {"done": cr.pk})
    cr.refresh_from_db()
    assert cr.status == "done"


def test_parent_cannot_close_other_family_request(client, hw):
    from apps.accounts.services import create_parent
    services.submit(hw, "косинус угла", "")
    p2 = create_parent("parent2", "VeryLongPass456", family_name="Б")
    client.force_login(p2.user)
    assert "косинус угла" not in client.get(reverse("parent_homework")).content.decode()
    assert client.post(reverse("parent_homework"), {"done": ContentRequest.objects.get().pk}).status_code == 404
