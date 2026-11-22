"""Освоение навыка (раздел 7 ТЗ). Чистые функции."""
from __future__ import annotations

WINDOW = 10
MASTERY_THRESHOLD = 0.8
ALMOST_THRESHOLD = 0.6


def weight(q: int) -> float:
    if q >= 4:
        return 1.0
    if q == 3:
        return 0.7
    if q == 2:
        return 0.4
    return 0.0


def push(window: list, q: int, day: str) -> list:
    """Добавить ответ в скользящее окно из 10 последних."""
    return (list(window) + [[weight(q), day]])[-WINDOW:]


def mastery_value(window: list) -> float:
    if not window:
        return 0.0
    return sum(w for w, _ in window) / len(window)


def distinct_days(window: list) -> int:
    return len({d for _, d in window})


def status(window: list, *, ever_mastered: bool = False, review_fail_streak: int = 0, placed: bool = False) -> str:
    """Статусы 7.2: not_started → learning → almost → mastered; refresh — после 2 провалов повторения."""
    n = len(window)
    if ever_mastered and review_fail_streak >= 2:
        return "refresh"
    if n == 0:
        return "almost" if placed else "not_started"
    m = mastery_value(window)
    if m >= MASTERY_THRESHOLD and n >= 8 and distinct_days(window) >= 2:
        return "mastered"
    if m >= ALMOST_THRESHOLD and n >= 6:
        return "almost"
    if placed and n < 6 and m >= ALMOST_THRESHOLD:
        return "almost"
    return "learning"


def is_unlocked(prereq_statuses: list[str]) -> bool:
    """MAS-1: следующий навык открыт, если все предварительные — «Почти» или выше."""
    return all(s in ("almost", "mastered", "refresh") for s in prereq_statuses)


def is_frustrated(window: list, lessons_done: int) -> bool:
    """MAS-2: после 3 уроков навык остаётся «Учу» с mastery < 0.4."""
    return lessons_done >= 3 and mastery_value(window) < 0.4


STATUS_VIEW = {
    "not_started": ("🏝️", "Ещё не начат"),
    "learning": ("🌱", "Учу"),
    "almost": ("🌷", "Почти освоено!"),
    "mastered": ("🌳", "Освоено!"),
    "refresh": ("🌳❓", "Давай освежим"),
}
