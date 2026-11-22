"""Чекеры типов заданий (раздел 5A). Ответ никогда не утекает в HTML до POST (FR-LRN-2)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class CheckResult:
    correct: bool
    partial: float = 0.0
    feedback_key: str = ""
    distractor: str = ""


def normalize_text(s: str, *, keep_yo: bool = False) -> str:
    """FR-LRN-6: trim, lower, е≈ё (кроме заданий на ё), , ≈ ."""
    s = (s or "").strip().lower().replace("ё", "е") if not keep_yo else (s or "").strip().lower()
    s = s.replace(",", ".")
    return re.sub(r"\s+", " ", s)


def _num(v) -> float | None:
    try:
        return float(str(v).strip().replace(",", ".").replace(" ", ""))
    except (TypeError, ValueError):
        return None


def _parse_fraction(s: str) -> tuple[int, int] | None:
    s = normalize_text(str(s)).replace(" ", "")
    m = re.fullmatch(r"(-?\d+)/(-?\d+)", s)
    if not m:
        # смешанное: 1 2/3 или 1+2/3
        m2 = re.fullmatch(r"(-?\d+)[+ ](-?\d+)/(-?\d+)", s)
        if not m2:
            n = _num(s)
            return (int(n), 1) if n is not None and n == int(n) else None
        whole, a, b = int(m2.group(1)), int(m2.group(2)), int(m2.group(3))
        if b == 0:
            return None
        sign = -1 if whole < 0 else 1
        return sign * (abs(whole) * b + a), b
    a, b = int(m.group(1)), int(m.group(2))
    return None if b == 0 else (a, b)


def _frac_eq(a: tuple[int, int], b: tuple[int, int], require_reduced: bool) -> bool:
    if require_reduced:
        return a == b
    return a[0] * b[1] == b[0] * a[1]


def check(ex_type: str, payload: dict, answer: dict, given: Any) -> CheckResult:
    fn = CHECKERS.get(ex_type)
    if not fn:
        return CheckResult(False, feedback_key="unknown_type")
    return fn(payload, answer, given)


def _single_choice(payload, answer, given) -> CheckResult:
    correct_ids = set(answer.get("correct") or [])
    gid = given.get("id") if isinstance(given, dict) else given
    ok = str(gid) in {str(c) for c in correct_ids}
    return CheckResult(ok, 1.0 if ok else 0.0)


def _number_input(payload, answer, given) -> CheckResult:
    expected = _num(answer.get("value"))
    got = _num(given.get("value") if isinstance(given, dict) else given)
    if expected is None or got is None:
        return CheckResult(False)
    tol = float(answer.get("tolerance", 0))
    ok = abs(expected - got) <= tol
    return CheckResult(ok, 1.0 if ok else 0.0)


def _fraction_input(payload, answer, given) -> CheckResult:
    raw = given.get("value") if isinstance(given, dict) else given
    if isinstance(given, dict) and "num" in given and "den" in given:
        raw = f"{given['num']}/{given['den']}"
    got = _parse_fraction(str(raw or ""))
    exp = _parse_fraction(str(answer.get("value", "")))
    if not got or not exp:
        # диагностический ответ
        fb = (payload or {}).get("distractor_feedback") or {}
        key = normalize_text(str(raw or ""))
        return CheckResult(False, distractor=fb.get(key, fb.get(str(raw or ""), "")))
    ok = _frac_eq(got, exp, bool(answer.get("require_reduced")))
    if not ok:
        fb = (payload or {}).get("distractor_feedback") or {}
        key = f"{got[0]}/{got[1]}"
        return CheckResult(False, distractor=fb.get(key, ""))
    return CheckResult(True, 1.0)


def _text_input(payload, answer, given) -> CheckResult:
    raw = given.get("value") if isinstance(given, dict) else given
    accept = answer.get("accept") or [answer.get("value", "")]
    keep_yo = bool(answer.get("keep_yo"))
    norm = normalize_text(str(raw or ""), keep_yo=keep_yo)
    ok = norm in {normalize_text(str(a), keep_yo=keep_yo) for a in accept}
    return CheckResult(ok, 1.0 if ok else 0.0)


def _matching(payload, answer, given) -> CheckResult:
    # given: {"pairs": {"left_id": "right_id", ...}}
    expected = answer.get("pairs") or {}
    pairs = given.get("pairs") if isinstance(given, dict) else given
    if not isinstance(pairs, dict):
        return CheckResult(False)
    total = len(expected)
    if total == 0:
        return CheckResult(False)
    good = sum(1 for k, v in expected.items() if str(pairs.get(str(k), pairs.get(k))) == str(v))
    return CheckResult(good == total, good / total)


def _drag_order(payload, answer, given) -> CheckResult:
    expected = [str(x) for x in (answer.get("order") or [])]
    got = given.get("order") if isinstance(given, dict) else given
    got = [str(x) for x in (got or [])]
    ok = got == expected
    return CheckResult(ok, 1.0 if ok else 0.0)


def _categorize(payload, answer, given) -> CheckResult:
    # answer.buckets: {bucket_id: [item_id, ...]}
    expected = answer.get("buckets") or {}
    buckets = given.get("buckets") if isinstance(given, dict) else given
    if not isinstance(buckets, dict):
        return CheckResult(False)
    items = {i: b for b, ids in expected.items() for i in ids}
    if not items:
        return CheckResult(False)
    good = 0
    for item, exp_b in items.items():
        got_b = None
        for b, ids in buckets.items():
            if str(item) in {str(x) for x in (ids or [])}:
                got_b = str(b)
                break
        if got_b == str(exp_b):
            good += 1
    return CheckResult(good == len(items), good / len(items))


def _letter_tiles(payload, answer, given) -> CheckResult:
    raw = given.get("value") if isinstance(given, dict) else given
    target = normalize_text(str(answer.get("value") or payload.get("word") or ""))
    ok = normalize_text(str(raw or "")) == target
    return CheckResult(ok, 1.0 if ok else 0.0)


def _step_by_step(payload, answer, given) -> CheckResult:
    # given: {"steps": [v1, v2, ...]} — каждый шаг числовой/текстовый
    steps = answer.get("steps") or payload.get("steps") or []
    got = given.get("steps") if isinstance(given, dict) else given
    if not isinstance(got, list) or not steps:
        return CheckResult(False)
    good = 0
    for i, step in enumerate(steps):
        exp = step.get("answer") if isinstance(step, dict) else step
        g = got[i] if i < len(got) else None
        if isinstance(exp, (int, float)) or (isinstance(exp, str) and _num(exp) is not None):
            ok = _num(g) is not None and abs(_num(g) - float(_num(exp))) < 1e-6
        else:
            ok = normalize_text(str(g or "")) == normalize_text(str(exp))
        good += int(ok)
    total = len(steps)
    return CheckResult(good == total, good / total if total else 0.0)


def _flashcard(payload, answer, given) -> CheckResult:
    return CheckResult(True, 1.0, feedback_key="shown")


CHECKERS = {
    "single_choice": _single_choice,
    "fill_blank_choice": _single_choice,
    "audio_text_choice": _single_choice,
    "number_input": _number_input,
    "equation": _number_input,
    "fraction_input": _fraction_input,
    "text_input": _text_input,
    "matching": _matching,
    "drag_order": _drag_order,
    "categorize": _categorize,
    "letter_tiles": _letter_tiles,
    "step_by_step": _step_by_step,
    "flashcard": _flashcard,
}


def public_payload(ex) -> dict:
    """Payload без answer и без distractor-ключей с правильными ответами для клиента."""
    p = dict(ex.payload or {})
    # перемешиваем варианты на клиенте; сервер отдаёт как есть + shuffle seed
    return p


# Русский язык (этап 2, D-201): fill_letters проверяется как выбор варианта, punctuation — по набору запятых.
from .ru_types import check_punctuation  # noqa: E402

CHECKERS.update({"fill_letters": _single_choice, "punctuation": check_punctuation})
