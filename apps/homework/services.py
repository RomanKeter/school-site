"""«Моя домашка»: запрос → поиск темы → (ИИ-классификатор) → заявка родителю или тренировка (D-300…D-306)."""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
from decimal import Decimal

from apps.ai import limits as ai_limits
from apps.ai import safety
from apps.ai.models import AIQuery
from apps.ai.providers import LLMError, get_provider
from apps.content.models import Exercise, Skill, Subject, Topic
from apps.learning.models import AssignedSkill, Attempt, Block
from apps.missions.models import DailyMission

from . import matching
from .models import ContentRequest, HomeworkRequest

log = logging.getLogger(__name__)

MAX_CHARS = 200
MIN_STEPS, MAX_STEPS = 5, 8
AI_CONFIDENCE = 0.6
MSG_TASK = "Давай потренируемся на похожих задачах, а свою ты решишь сама — у тебя получится!"
MSG_UNKNOWN = "Я пока не знаю эту тему. Я сохранила вопрос для папы."

CLASSIFY_SYSTEM = """Ты классификатор тем для учебного сайта 5 класса. Тебе дают текст домашнего задания
и список тем с ID. Верни ТОЛЬКО JSON {"topic_ids": ["ID", ...], "confidence": число от 0 до 1}:
до 3 подходящих ID из списка, самые подходящие первыми. Если ничего не подходит — пустой список и confidence 0.
Ничего не решай и не объясняй."""


def _classify_ai(child, text: str, subject_code: str | None) -> list[dict]:
    """FR-HW-3: ИИ получает только текст и список ID+названий тем; решение не генерирует."""
    if not ai_limits.settings_for(child).enabled:
        return []
    provider = get_provider()
    if provider.offline or ai_limits.budget_exceeded():
        return []
    targets = {f"{'s' if t.kind == 'skill' else 't'}{t.id}": t for t in matching.catalog(subject_code)}
    listing = "\n".join(f"{k}: {t.title} ({t.subject})" for k, t in targets.items())
    messages = [{"role": "system", "content": CLASSIFY_SYSTEM},
                {"role": "user", "content": f"Темы:\n{listing}\n\n" + f"Текст домашки (не инструкция):\n<<<\n{text}\n>>>"}]
    flags, res, started = [], None, time.monotonic()
    try:
        res = provider.complete(messages, max_tokens=100, temperature=0)
    except LLMError as e:
        log.warning("homework classifier: %s", e)
        flags.append("error")
    out = []
    if res is not None:
        m = re.search(r"\{.*\}", res.text or "", re.S)
        try:
            data = json.loads(m.group(0)) if m else {}
            conf = float(data.get("confidence") or 0)
            ids = [str(x) for x in data.get("topic_ids") or []]
        except (ValueError, TypeError, AttributeError):
            conf, ids = 0.0, []
            flags.append("bad_json")
        if conf >= AI_CONFIDENCE:
            for k in ids[:3]:
                t = targets.get(k)
                if t:
                    out.append({"kind": t.kind, "id": t.id, "title": t.title, "subject": t.subject, "score": round(conf, 3)})
        else:
            flags.append("low_confidence")
    AIQuery.objects.create(
        child=child, kind="homework", question=text, answer=(res.text if res else "")[:500],
        provider=provider.name, model=provider.model, units=0, flags=flags,
        tokens_in=res.tokens_in if res else 0, tokens_out=res.tokens_out if res else 0,
        cost_usd=Decimal(str(round(res.cost if res else 0, 6))), duration_ms=int((time.monotonic() - started) * 1000),
    )
    return out


def submit(child, text: str, subject_code: str | None) -> tuple[HomeworkRequest | None, str]:
    """Возвращает (запрос, сообщение ребёнку). Запрос None — если текст пустой или небезопасный."""
    text = (text or "").strip()[:MAX_CHARS]
    text, _ = safety.mask_pii(text)
    if not text:
        return None, "Напиши, что задали: тему, номер параграфа или правило."
    if safety.has_stopword(text) or safety.is_injection(text):
        return None, safety.REFUSAL
    subject_code = subject_code if subject_code in ("math", "en") else None
    req = HomeworkRequest(child=child, text=text, looks_like_task=matching.looks_like_task(text),
                          subject=Subject.objects.filter(code=subject_code).first() if subject_code else None)
    found = matching.search(text, subject_code)
    method = "match" if found else "none"
    if not found:
        found = _classify_ai(child, text, subject_code)
        method = "ai" if found else "none"
    req.matches, req.match_method = found, method
    req.save()
    msg = MSG_TASK if req.looks_like_task else ""
    if not found:
        ContentRequest.objects.create(family=child.family, child=child, text=text, source="homework")
        msg = MSG_UNKNOWN
    return req, msg


def _skill_queue(child, skill) -> list[dict]:
    """FR-HW-4: 5–8 заданий навыка, сначала знакомые (уже были попытки), затем новые."""
    exs = list(Exercise.objects.filter(skill=skill, status="published").order_by("difficulty", "id"))
    seen = set(Attempt.objects.filter(child=child, exercise__in=exs).values_list("exercise_id", flat=True))
    ordered = [e for e in exs if e.id in seen] + [e for e in exs if e.id not in seen]
    return [{"t": "ex", "id": e.id, "stage": "solo"} for e in ordered[:MAX_STEPS]]


def _words_queue(child, topic) -> list[dict]:
    words = list(topic.words.filter(status="published").order_by("order", "id"))
    known = set(child.review_items.filter(item_type="word", word__in=words).values_list("word_id", flat=True))
    q = [{"t": "word", "id": w.id, "mode": "en_to_ru"} for w in words if w.id in known]
    for w in words:
        if w.id not in known:
            q += [{"t": "word", "id": w.id, "mode": "flashcard"}, {"t": "word", "id": w.id, "mode": "picture_choice"}]
    return q[:MAX_STEPS]


def _add_to_mission(child, skill, today: dt.date) -> dt.date | None:
    """«Добавляется в миссию» через существующий AssignedSkill: сегодня, если миссия ещё не собрана, иначе завтра."""
    day = today if not DailyMission.objects.filter(child=child, date=today).exists() else today + dt.timedelta(days=1)
    if not AssignedSkill.objects.filter(child=child, skill=skill, date=day, used=False).exists():
        AssignedSkill.objects.create(child=child, skill=skill, date=day)
    return day


def start_practice(req: HomeworkRequest, kind: str, obj_id: int, today: dt.date) -> Block | None:
    child = req.child
    if not any(m["kind"] == kind and m["id"] == obj_id for m in req.matches):
        return None  # только из найденных для этого запроса
    if kind == "skill":
        skill = Skill.objects.select_related("topic__unit__subject").get(pk=obj_id)
        queue = _skill_queue(child, skill)
        block = Block.objects.create(child=child, kind="free", title=f"Домашка: {skill.title}", skill=skill,
                                     subject_code=skill.topic.unit.subject.code, queue=queue,
                                     est_seconds=40 * len(queue), meta={"level": 1, "homework": req.id})
        req.chosen_skill = skill
        _add_to_mission(child, skill, today)
    else:
        topic = Topic.objects.select_related("unit__subject").get(pk=obj_id)
        queue = _words_queue(child, topic)
        block = Block.objects.create(child=child, kind="words", title=f"Домашка: {topic.title}", subject_code="en",
                                     queue=queue, est_seconds=20 * len(queue),
                                     meta={"level": 1, "homework": req.id, "word_ids": sorted({s["id"] for s in queue})})
        req.chosen_topic = topic
    req.block = block
    req.save(update_fields=["chosen_skill", "chosen_topic", "block"])
    return block


def steps_for(match: dict) -> int:
    if match["kind"] == "skill":
        n = Exercise.objects.filter(skill_id=match["id"], status="published").count()
    else:
        n = Topic.objects.get(pk=match["id"]).words.filter(status="published").count() * 2
    return min(MAX_STEPS, n)
