"""Русский язык (этап 2, D-200..): новые типы заданий поверх существующего движка.

fill_letters — вставь букву/буквосочетание (проверка как single_choice по id варианта);
punctuation — поставь запятые: ответ = множество индексов слов, после которых нужна запятая.
"""

RU_TYPES = ("fill_letters", "punctuation")


def check_punctuation(payload, answer, given):
    from .checkers import CheckResult  # ленивый импорт: checkers импортирует этот модуль

    raw = given.get("commas") if isinstance(given, dict) else given
    try:
        got = {int(x) for x in (raw or [])}
    except (TypeError, ValueError):
        return CheckResult(False)
    need = {int(x) for x in (answer.get("commas") or [])}
    if got == need:
        return CheckResult(True, 1.0)
    hit = len(got & need)
    partial = hit / max(len(need | got), 1)
    distractor = ""
    if need - got and not got - need:
        distractor = "Почти! Запятых должно быть больше."
    elif got - need and not need - got:
        distractor = "Почти! Одна запятая лишняя."
    return CheckResult(False, partial, distractor=distractor)


def punctuated(words, commas):
    """Собирает предложение с запятыми после слов с индексами commas."""
    commas = {int(c) for c in commas or []}
    return " ".join(w + ("," if i in commas else "") for i, w in enumerate(words or []))


def answer_text(exercise):
    """Правильный ответ целиком (для показа после исчерпания попыток)."""
    p, a = exercise.payload or {}, exercise.answer or {}
    if exercise.type == "punctuation":
        return punctuated(p.get("words"), a.get("commas"))
    if exercise.type == "fill_letters":
        parts = p.get("parts") or ["", ""]
        right = (a.get("correct") or [""])[0]
        return f"{parts[0]}{right}{parts[1] if len(parts) > 1 else ''}"
    return ""
