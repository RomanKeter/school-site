"""«Научи Масю» (раздел 23.3 ТЗ, метод Фейнмана; D-106, D-107).

Ребёнок объясняет освоенную тему своими словами, ИИ сверяет с ключевыми идеями (FeynmanTopic.key_points),
Мася хвалит конкретную мысль и задаёт 1–2 наивных вопроса. Звёзды: +5 за объяснение, +3 если покрыты все идеи
(IMP-FEYN-5), не чаще одного раза в 3 дня на навык. На mastery не влияет.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
from decimal import Decimal

from django.utils import timezone

from apps.learning.models import SkillMastery
from apps.rewards.stars import award

from . import limits, prompts, safety
from .models import AIQuery, FeynmanSession, FeynmanTopic
from .providers import FakeProvider, LLMError, get_provider

log = logging.getLogger(__name__)

MAX_ROUNDS = 3  # объяснение + 2 уточняющих вопроса Маси
MAX_CHARS = 500
STARS_TRY, STARS_FULL = 5, 3
STARS_EVERY_DAYS = 3
ELIGIBLE = ("almost", "mastered")


def topics_for(child):
    """[(FeynmanTopic, открыта ли)] — открыты темы со статусом «Почти» или «Освоен» (IMP-FEYN-1)."""
    status = dict(SkillMastery.objects.filter(child=child).values_list("skill_id", "status"))
    out = []
    for t in FeynmanTopic.objects.filter(enabled=True, skill__status="published").select_related("skill__topic__unit__subject"):
        out.append((t, status.get(t.skill_id) in ELIGIBLE))
    return out


def is_open(child, skill) -> bool:
    return SkillMastery.objects.filter(child=child, skill=skill, status__in=ELIGIBLE).exists()


def current_session(child, skill) -> FeynmanSession:
    s = FeynmanSession.objects.filter(child=child, skill=skill, finished=False).first()
    return s or FeynmanSession.objects.create(child=child, skill=skill)


# ---------- оценка ----------

def _stem_hit(text: str, kw: str) -> bool:
    kw = kw.lower().replace("ё", "е").strip()
    return bool(kw) and re.search(r"(?<!\w)" + re.escape(kw), text) is not None


def offline_evaluate(points: list[dict], text: str) -> dict:
    t = (text or "").lower().replace("ё", "е")
    covered = [i for i, p in enumerate(points) if any(_stem_hit(t, k) for k in p.get("keywords") or [])]
    missing = [i for i in range(len(points)) if i not in covered]
    return {"covered": covered, "missing": missing, "misconception": None, "reply": ""}


def _parse_llm(raw: str, n: int) -> dict | None:
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except ValueError:
        return None

    def idx(xs):
        out = []
        for x in xs or []:
            try:
                i = int(x) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= i < n and i not in out:
                out.append(i)
        return out

    if not isinstance(data, dict) or not isinstance(data.get("reply", ""), str):
        return None
    covered = idx(data.get("covered"))
    return {"covered": covered, "missing": [i for i in range(n) if i not in covered],
            "misconception": data.get("misconception") if isinstance(data.get("misconception"), str) else None,
            "reply": data.get("reply") or ""}


def offline_reply(points: list[dict], new: list[int], all_covered: set, last_round: bool) -> str:
    parts = []
    missing = [i for i in range(len(points)) if i not in all_covered]
    if new:
        parts.append(f"Ого! Ты объяснила, что {points[new[0]]['text'].rstrip('.')}." + ("" if not missing else " Я поняла!"))
    else:
        parts.append("Спасибо, что объясняешь мне!")
    if not missing:
        parts.append("Теперь я всё-всё поняла. Спасибо, ты настоящая учительница!")
    elif last_round:
        parts.append("Кажется, я почти разобралась. Спасибо за урок!")
    else:
        parts.append(points[missing[0]].get("ask") or "А что ещё важно помнить?")
    return " ".join(parts)


def submit(session: FeynmanSession, text: str, today: dt.date) -> dict:
    """Один раунд объяснения. Возвращает {"reply", "finished", "blocked", "refused", "stars"}."""
    topic = session.skill.feynman
    points = topic.key_points or []
    flags: list[str] = []
    text = (text or "").strip()[:MAX_CHARS]
    text, pii = safety.mask_pii(text)
    if pii:
        flags.append("pii")
    if not text:
        return {"reply": "Расскажи мне своими словами — я внимательно слушаю!", "finished": False, "blocked": True, "refused": False, "stars": 0}
    if safety.has_stopword(text) or safety.is_injection(text):
        flags.append("stopword" if safety.has_stopword(text) else "injection")
        AIQuery.objects.create(child=session.child, kind="teach", skill=session.skill, question=text,
                               answer=safety.REFUSAL, provider="filter", flags=flags, refused=True, units=0)
        return {"reply": safety.REFUSAL, "finished": False, "blocked": False, "refused": True, "stars": 0}

    units = 1.0 if session.rounds == 0 else 0.0  # IMP-FEYN-6: одно объяснение = один вопрос
    blocked = limits.check(session.child, today, units)
    if blocked:
        return {"reply": blocked, "finished": False, "blocked": True, "refused": False, "stars": 0}
    limits.touch(session.child)

    session.rounds += 1
    last_round = session.rounds >= MAX_ROUNDS
    provider = get_provider()
    if not provider.offline and limits.budget_exceeded():
        flags.append("budget")
        provider = FakeProvider()

    started = time.monotonic()
    result, t_in, t_out, cost = None, 0, 0, 0.0
    if not provider.offline:
        pts = "\n".join(f"{i + 1}. {p['text']}" for i, p in enumerate(points))
        history = "\n".join(f"{'Ученица' if h['who'] == 'child' else 'Мася'}: {h['text']}" for h in session.history[-4:])
        if session.covered:
            history += "\nУже объяснено раньше (про это не спрашивай): " + ", ".join(str(i + 1) for i in session.covered)
        messages = [
            {"role": "system", "content": prompts.TEACH_SYSTEM.format(skill=session.skill.title, points=pts)},
            {"role": "user", "content": (f"Предыдущий разговор:\n{history}\n\n" if history else "")
             + prompts.CHILD_FRAME.format(text=text)},
        ]
        try:
            res = provider.complete(messages, max_tokens=400, temperature=0.3)
            t_in, t_out, cost = res.tokens_in, res.tokens_out, res.cost
            result = _parse_llm(res.text, len(points))
            if result is None:
                flags.append("bad_json")
        except LLMError as e:
            log.warning("AI teach: %s", e)
            flags.append("error")
    offline = result is None
    if offline:
        if not provider.offline:
            flags.append("fallback")
        result = offline_evaluate(points, text)

    before = set(session.covered)
    all_cov = before | set(result["covered"])
    new = [i for i in result["covered"] if i not in before]
    reply = result.get("reply") or ""
    if reply:
        reply, had_url = safety.strip_urls(reply)
        if had_url:
            flags.append("url")
        if safety.has_harsh(reply) or safety.has_stopword(reply):
            flags.append("harsh")
            reply = ""
    all_done = len(all_cov) >= len(points)
    if all_done and "?" in reply:
        flags.append("finale")
        reply = ""  # всё объяснено — Мася благодарит, а не задаёт вопрос
    if not reply:
        reply = offline_reply(points, new, all_cov, last_round)
    reply = safety.limit_words(reply, 60)

    session.covered = sorted(all_cov)
    session.ai_result = result
    session.child_text = (session.child_text + "\n" + text).strip()
    session.history = session.history + [{"who": "child", "text": text}, {"who": "masya", "text": reply}]
    finished = last_round or all_done
    session.save()
    AIQuery.objects.create(
        child=session.child, kind="teach", skill=session.skill, question=text, answer=reply,
        provider="offline" if offline else provider.name, model="" if offline else provider.model,
        tokens_in=t_in, tokens_out=t_out, cost_usd=Decimal(str(round(cost, 6))), units=units, flags=flags,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    stars = finish(session, today) if finished else 0
    return {"reply": reply, "finished": finished, "blocked": False, "refused": False, "stars": stars}


def finish(session: FeynmanSession, today: dt.date) -> int:
    """Завершить сессию и начислить звёзды (не чаще раза в 3 дня на навык; без объяснения — без звёзд)."""
    if session.finished:
        return 0
    session.finished = True
    session.finished_at = timezone.now()
    stars = 0
    since = timezone.now() - dt.timedelta(days=STARS_EVERY_DAYS)
    recent = FeynmanSession.objects.filter(child=session.child, skill=session.skill, stars_awarded__gt=0,
                                           finished_at__gte=since).exclude(pk=session.pk).exists()
    if session.rounds > 0 and not recent:
        stars += award(session.child, STARS_TRY, "teach", session.pk, today)
        points = session.skill.feynman.key_points or []
        if points and len(session.covered) >= len(points):
            stars += award(session.child, STARS_FULL, "teach_full", session.pk, today)
    session.stars_awarded = stars
    session.save()
    return stars
