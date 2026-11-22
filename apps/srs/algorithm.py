"""Интервальное повторение — модифицированный SM-2 (раздел 6 ТЗ).

Чистые функции без доступа к БД (SR-6): их легко тестировать и менять.
"""
from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, replace
from typing import Protocol


class Rng(Protocol):
    def uniform(self, a: float, b: float) -> float: ...


@dataclass(frozen=True)
class SrsParams:
    initial_ef: float = 2.5
    min_ef: float = 1.3
    max_ef: float = 2.8
    i_max: int = 60
    steps: tuple = (1, 3, 7)
    fuzz_pct: float = 0.10

    @classmethod
    def from_settings(cls):
        from django.conf import settings

        s = getattr(settings, "SRS", {})
        return cls(
            initial_ef=s.get("initial_ef", 2.5),
            min_ef=s.get("min_ef", 1.3),
            max_ef=s.get("max_ef", 2.8),
            i_max=s.get("i_max", 60),
            steps=tuple(s.get("steps", (1, 3, 7))),
            fuzz_pct=s.get("fuzz_pct", 0.10),
        )


@dataclass(frozen=True)
class CardState:
    n: int
    ef: float
    interval: int
    due: dt.date
    last_reviewed: dt.date | None = None
    lapses: int = 0


def new_card(today: dt.date, params: SrsParams = SrsParams()) -> CardState:
    """Создание карточки (знакомство / первый урок / первая ошибка): n=0, I=1, показ завтра."""
    first = params.steps[0]
    return CardState(n=0, ef=params.initial_ef, interval=first, due=today + dt.timedelta(days=first))


def update_ef(ef: float, q: int, params: SrsParams = SrsParams()) -> float:
    ef2 = ef + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    return round(max(params.min_ef, min(params.max_ef, ef2)), 4)


def apply_fuzz(interval: int, rng: Rng | None, params: SrsParams = SrsParams()) -> int:
    """Для I ≥ 7 — случайное смещение ±10 %, округление до дня; результат в [1; I_max]."""
    if interval < 7 or rng is None or params.fuzz_pct <= 0:
        return interval
    delta = rng.uniform(-params.fuzz_pct, params.fuzz_pct) * interval
    return max(1, min(params.i_max, int(round(interval + delta))))


def schedule(state: CardState, q: int, today: dt.date, rng: Rng | None = None,
             params: SrsParams = SrsParams()) -> CardState:
    """schedule(state, q, today, rng) -> new_state (SR-6).

    q < 3 — неуспех: n=0, I=1 («повторить завтра»).
    q ≥ 3 — успех: n+1; n=1 → 3 дня, n=2 → 7 дней, n≥3 → round(I_prev × EF').
    SR-3: верный ответ на карточку, просроченную на d дней, считается от I_prev + d/2.
    """
    if not 0 <= q <= 5:
        raise ValueError("q должно быть в диапазоне 0..5")
    ef = update_ef(state.ef, q, params)
    if q < 3:
        return replace(
            state, n=0, ef=ef, interval=params.steps[0],
            due=today + dt.timedelta(days=params.steps[0]),
            last_reviewed=today, lapses=state.lapses + 1,
        )
    n = state.n + 1
    if n == 1:
        interval = params.steps[1]
    elif n == 2:
        interval = params.steps[2]
    else:
        overdue = max(0, (today - state.due).days)
        base = state.interval + overdue / 2
        interval = int(round(base * ef))
    interval = max(1, min(interval, params.i_max))
    interval = apply_fuzz(interval, rng, params)
    return replace(state, n=n, ef=ef, interval=interval,
                   due=today + dt.timedelta(days=interval), last_reviewed=today)


def quality(*, correct: bool, attempt_no: int, hints_used: int, duration_s: float,
            est_seconds: int, skipped: bool = False) -> int:
    """Оценка качества ответа q (0–5) — таблица 6.2. Ребёнок себя не оценивает."""
    if skipped:
        return 0
    if not correct:
        return 1
    if attempt_no >= 3 or hints_used >= 2:
        return 2
    if attempt_no == 2 or hints_used == 1:
        return 3
    if duration_s <= 1.5 * est_seconds:
        return 5
    return 4


def default_rng():
    return random.Random()
