"""«Спросить Масю» — сократические подсказки к текущему заданию (раздел 9 ТЗ, D-102…D-105).

Конвейер: предфильтр (ПДн, стоп-словарь, подмена инструкций) → лимиты → вызов LLMProvider
→ постфильтр (ссылки, длина, стоп-слова, утечка ответа с повторным запросом) → журнал AIQuery.
Без ключа или при любом сбое — офлайн-подсказка из материалов сайта. Исключения наружу не выходят.
"""
from __future__ import annotations

import logging
import time
from decimal import Decimal

from . import limits, prompts, safety
from .models import AIQuery
from .providers import FakeProvider, LLMError, get_provider

log = logging.getLogger(__name__)

MAX_TURNS = 3  # FR-AI-1: не больше 3 уточнений на одно задание
MAX_WORDS = 90
SIMILAR = "Давай разберём на похожем примере."


def _task_text(exercise) -> str:
    p = exercise.payload or {}
    text = p.get("prompt", "")
    opts = [o.get("text") for o in p.get("options") or [] if isinstance(o, dict) and o.get("text")]
    if opts:
        text += "\nВарианты: " + "; ".join(opts)
    return text


def offline_reply(exercise, turn: int) -> str:
    """Подсказка без ИИ: правило + подсказка нужного уровня + наводящий вопрос. Проверяется на утечку."""
    skill = exercise.skill
    hints = [h.get("text", "") for h in (exercise.payload or {}).get("hints") or [] if isinstance(h, dict)]
    # предпочитаем подсказки без готового ответа; если таких нет — авторские подсказки сайта
    # (их и так показывает кнопка «Подсказка», они проверены автором контента)
    hints = [h for h in hints if h and not safety.leaks_answer(h, exercise)] or [h for h in hints if h]
    parts = []
    if turn == 1 and skill.rule_card and not safety.leaks_answer(skill.rule_card, exercise):
        parts.append(f"Вспомним правило: {skill.rule_card}")
    if hints:
        parts.append(hints[min(turn, len(hints)) - 1])
    parts.append("Как ты думаешь, какой шаг сделать первым?" if turn == 1 else "Что у тебя получается на этом шаге?")
    text = " ".join(p for p in parts if p)
    if safety.leaks_answer(text, exercise) and not hints:
        text = f"{SIMILAR} " + (f"Правило: {skill.rule_card} " if skill.rule_card and not safety.leaks_answer(skill.rule_card, exercise) else "") + \
            "Попробуй сделать первый шаг сама — что ты заметила в задании?"
    return text


def _postfilter(text: str, flags: list) -> str | None:
    text, had_url = safety.strip_urls(text.replace("$", "").replace("**", ""))
    if had_url:
        flags.append("url")
    if safety.has_stopword(text):
        flags.append("stopword_out")
        return None
    text, _ = safety.mask_pii(text)
    return safety.limit_words(text, MAX_WORDS)


def ask(child, exercise, question: str, *, turn: int, prev_answer: str, today) -> dict:
    """Возвращает {"text", "turn", "can_more", "offline", "refused", "blocked"}; никогда не бросает исключения."""
    turn = max(1, min(int(turn or 1), MAX_TURNS))
    flags: list[str] = []
    q = (question or "").strip()[:200]
    q, pii = safety.mask_pii(q)
    if pii:
        flags.append("pii")
    units = 1.0 if turn == 1 else 0.5  # AI-1: уточнения — ½ вопроса

    if q and (safety.has_stopword(q) or safety.is_injection(q)):
        flags.append("stopword" if safety.has_stopword(q) else "injection")
        AIQuery.objects.create(child=child, kind="hint", skill=exercise.skill, exercise=exercise, question=q,
                               answer=safety.REFUSAL, provider="filter", flags=flags, refused=True, units=0)
        return {"text": safety.REFUSAL, "turn": turn, "can_more": False, "offline": True, "refused": True, "blocked": False}

    blocked = limits.check(child, today, units)
    if blocked:
        return {"text": blocked, "turn": turn, "can_more": False, "offline": True, "refused": False, "blocked": True}
    limits.touch(child)

    provider = get_provider()
    if not provider.offline and limits.budget_exceeded():
        flags.append("budget")
        provider = FakeProvider()

    skill = exercise.skill
    system = prompts.HINT_SYSTEM.format(
        subject=skill.topic.unit.subject.title, topic=skill.topic.title, skill=skill.title,
        rule_card=skill.rule_card or "—",
    )
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": prompts.TASK_FRAME.format(task=_task_text(exercise))}]
    if prev_answer:
        messages.append({"role": "assistant", "content": prev_answer[:800]})
    messages.append({"role": "user", "content": prompts.CHILD_FRAME.format(text=q or "Я не знаю, с чего начать. Помоги, пожалуйста.")})

    started = time.monotonic()
    text, t_in, t_out, cost = None, 0, 0, 0.0
    if not provider.offline:
        for attempt in (1, 2):
            try:
                res = provider.complete(messages, max_tokens=400, temperature=0.3)
            except LLMError as e:
                log.warning("AI helper: %s", e)
                flags.append("error")
                break
            t_in, t_out, cost = t_in + res.tokens_in, t_out + res.tokens_out, cost + res.cost
            candidate = _postfilter(res.text, flags)
            if candidate and not safety.leaks_answer(candidate, exercise):
                text = candidate
                break
            if candidate:
                flags.append("leak")
            if attempt == 1:
                flags.append("retry")
                messages = messages + [{"role": "system", "content": prompts.HINT_STRICT}]
    offline = text is None
    if offline:
        if not provider.offline:
            flags.append("fallback")
        text = offline_reply(exercise, turn)

    AIQuery.objects.create(
        child=child, kind="hint", skill=skill, exercise=exercise, question=q, answer=text,
        provider=provider.name if not offline else "offline", model=provider.model if not offline else "",
        tokens_in=t_in, tokens_out=t_out, cost_usd=Decimal(str(round(cost, 6))), units=units, flags=flags,
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    return {"text": text, "turn": turn, "can_more": turn < MAX_TURNS, "offline": offline, "refused": False, "blocked": False}
