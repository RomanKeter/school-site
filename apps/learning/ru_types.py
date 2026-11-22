"""Русский язык (этап 2, D-200..): новые типы заданий поверх существующего движка.

fill_letters — вставь букву/буквосочетание (проверка как single_choice по id варианта; id "0" — «ничего не пишем»);
punctuation — поставь запятые: ответ = множество индексов слов, после которых нужна запятая;
morphemes — разбор слова по составу (FR-RU-4, D-207): каждой букве — метка морфемы
    p — приставка, k — корень, s — суффикс, o — окончание; плюс флаг «нулевое окончание»;
dictation — диктант (FR-RU-5, D-208): текст озвучивается ru-RU, ребёнок пишет, сравнение по словам.
"""
import base64
import re

RU_TYPES = ("fill_letters", "punctuation", "morphemes", "dictation")
MORPH_NAMES = {"p": "приставка", "k": "корень", "s": "суффикс", "o": "окончание"}


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
    if exercise.type == "morphemes":
        return morph_text(p.get("word", ""), a.get("labels", ""), a.get("zero"))
    if exercise.type == "dictation":
        return a.get("value", "")
    if exercise.type == "fill_letters":
        parts = p.get("parts") or ["", ""]
        right = (a.get("correct") or [""])[0]
        right = "" if right == "0" else right
        return f"{parts[0]}{right}{parts[1] if len(parts) > 1 else ''}"
    return ""


# ---------- Разбор слова по составу ----------

def segments(word, labels):
    """[('p','под'), ('k','окон'), ...] — подряд идущие буквы с одной меткой (в контенте нет двух суффиксов подряд)."""
    out, cur, cl = [], "", None
    for ch, lb in zip(word, labels):
        if lb != cl and cur:
            out.append((cl, cur)); cur = ""
        cl = lb; cur += ch
    if cur:
        out.append((cl, cur))
    return out


def morph_text(word, labels, zero):
    segs = segments(word, labels)
    parts = "-".join(t for _, t in segs) + ("-□" if zero else "")
    names = [f"{MORPH_NAMES.get(m, m)} {t}" for m, t in segs]
    if zero:
        names.append("нулевое окончание")
    return f"{parts} ({', '.join(names)})"


def check_morphemes(payload, answer, given):
    from .checkers import CheckResult

    need = answer.get("labels") or ""
    zero = bool(answer.get("zero"))
    got = (given.get("labels") if isinstance(given, dict) else "") or ""
    gzero = bool(given.get("zero")) if isinstance(given, dict) else False
    if len(got) != len(need) or "-" in got:
        return CheckResult(False, distractor="Отметь каждую букву слова.")
    if got == need and gzero == zero:
        return CheckResult(True, 1.0)
    right = sum(a == b for a, b in zip(got, need)) + (gzero == zero)
    partial = right / (len(need) + 1)
    wrong = [MORPH_NAMES[m] for m in "pkso" if any((a == m) != (b == m) for a, b in zip(got, need))]
    if gzero != zero and "окончание" not in wrong:
        wrong.append("окончание")
    return CheckResult(False, partial, distractor="Проверь: " + ", ".join(wrong) + ".")


# ---------- Диктант ----------

_TOKEN = re.compile(r"[а-яёa-z0-9-]+|[,:;!?—]", re.I)


def dict_tokens(text):
    t = (text or "").lower().replace("ё", "е").replace("–", "—").replace(" - ", " — ")
    return _TOKEN.findall(t)


def check_dictation(payload, answer, given):
    from .checkers import CheckResult

    raw = given.get("value") if isinstance(given, dict) else given
    need, got = dict_tokens(answer.get("value")), dict_tokens(raw)
    if got == need:
        return CheckResult(True, 1.0)
    words_need = [t for t in need if t[0].isalnum()]
    words_got = [t for t in got if t[0].isalnum()]
    bad = [i + 1 for i, w in enumerate(words_need) if i >= len(words_got) or words_got[i] != w]
    if not bad and len(words_got) == len(words_need):
        return CheckResult(False, 0.9, distractor="Слова написаны верно — проверь знаки препинания.")
    ok = len(words_need) - len(bad)
    if len(words_got) != len(words_need):
        tip = f"Проверь, все ли слова записаны: их должно быть {len(words_need)}."
    else:
        tip = "Проверь " + ("слово № " if len(bad) == 1 else "слова № ") + ", ".join(map(str, bad[:4])) + "."
    return CheckResult(False, ok / max(len(words_need), 1), distractor=tip)


def say_b64(text):
    """Текст для озвучки кладётся в HTML в base64: озвучка в браузере без сервера, ответ не виден глазами."""
    return base64.b64encode((text or "").encode("utf-8")).decode()
