"""Подстройка сложности (принятое улучшение №2).

3 верных подряд → чуть сложнее; 2 ошибки подряд → чуть легче.
Ребёнок НИКОГДА не видит слов «уровень понижен» — уровень живёт только в данных блока.
"""
from __future__ import annotations

from dataclasses import dataclass

MIN_LEVEL, MAX_LEVEL = 1, 3


@dataclass(frozen=True)
class AdaptiveState:
    level: int = 1
    right_streak: int = 0
    wrong_streak: int = 0


def update(state: AdaptiveState, correct_first_try: bool) -> AdaptiveState:
    """«Верно» здесь — верно с первой попытки без подсказки; всё остальное считается промахом."""
    if correct_first_try:
        right = state.right_streak + 1
        if right >= 3:
            return AdaptiveState(min(MAX_LEVEL, state.level + 1), 0, 0)
        return AdaptiveState(state.level, right, 0)
    wrong = state.wrong_streak + 1
    if wrong >= 2:
        return AdaptiveState(max(MIN_LEVEL, state.level - 1), 0, 0)
    return AdaptiveState(state.level, 0, wrong)


def pick_difficulty(available: set[int], level: int) -> int | None:
    """Ближайшая доступная сложность к целевому уровню (при равенстве — более лёгкая)."""
    if not available:
        return None
    return min(available, key=lambda d: (abs(d - level), d))
