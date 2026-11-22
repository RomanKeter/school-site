"""Фильтры ввода и вывода (раздел 9.3 ТЗ, D-103): маскирование ПДн, стоп-словарь, ссылки, утечка ответа."""
from __future__ import annotations

import re

MASK = "[скрыто]"

_PII = [
    re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),  # e-mail
    re.compile(r"(?:\+?\d[\s()-]*){9,}\d"),  # телефон
    re.compile(r"(?i)\b(?:меня\s+зовут|моё\s+имя|мое\s+имя|my\s+name\s+is)\s+[^\s,.!?]+(?:\s+[А-ЯЁA-Z][^\s,.!?]*)?"),
    re.compile(r"(?i)\b(?:я\s+живу|живу\s+на|живу\s+в|мой\s+адрес|адрес)\b[^.!?\n]{0,60}"),
    re.compile(r"(?i)\b(?:школ[аеуы]?|гимнази[яиюей]|лице[йяю])\s*(?:№|N|номер)?\s*\d+"),
    re.compile(r"(?i)\b(?:ул\.|улица|проспект|пр-т|дом|кв\.|квартира)\s*[\wА-Яа-яЁё.-]*\s*\d+"),
]

# Стоп-словарь небезопасных и внеучебных тем (основа; родитель расширит в этапе 2+, см. открытые вопросы).
STOP_WORDS = [
    "убить", "убей", "убийств", "смерть", "умереть", "самоубий", "кровь", "оружи", "пистолет", "бомб",
    "наркот", "сигарет", "алкогол", "пиво", "водк", "секс", "голая", "голый", "порн", "страшилк",
    "политик", "войн", "президент", "религи", "суицид", "насили", "драться", "драку", "ненавиж",
]
# Попытки подменить инструкции (prompt injection) — тоже отказ без вызова ИИ.
INJECTION = [
    "забудь все правила", "забудь правила", "забудь инструкц", "игнорируй", "ignore previous", "ignore all",
    "ты больше не", "системн", "system prompt", "притворись", "представь что ты не",
]
# Слова, запрещённые в ответах Маси (DS-26, IMP-FEYN-4).
HARSH = ["неправильно", "ошибка", "ошибся", "ошиблась", "неверно", "плохо", "глупо"]

REFUSAL = "Я помогаю только со школьными темами. Спроси меня про учёбу или попроси помощи у взрослых."

_URL = re.compile(r"(?i)\b(?:https?://|www\.)\S+|\b[\w-]+\.(?:ru|by|com|org|net|io|ai)\b\S*")


def _norm(text: str) -> str:
    return (text or "").lower().replace("ё", "е")


def mask_pii(text: str) -> tuple[str, bool]:
    out = text or ""
    for rx in _PII:
        out = rx.sub(MASK, out)
    return out, out != (text or "")


_STOP_RX = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(w) for w in STOP_WORDS) + ")")


def has_stopword(text: str) -> bool:
    """Совпадение только с начала слова: «двойной» не ловится по «войн»."""
    return bool(_STOP_RX.search(_norm(text)))


def is_injection(text: str) -> bool:
    t = _norm(text)
    return any(w in t for w in INJECTION)


def strip_urls(text: str) -> tuple[str, bool]:
    out = _URL.sub("", text or "")
    return out, out != (text or "")


def has_harsh(text: str) -> bool:
    t = _norm(text)
    return any(w in t for w in HARSH)


def limit_words(text: str, max_words: int) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return (text or "").strip()
    cut = " ".join(words[:max_words]).rstrip(",;:—-")
    return cut + "…"


# ---------- Утечка ответа (9.3 п. 6) ----------

def _norm_answer(s) -> str:
    s = _norm(str(s)).strip()
    s = re.sub(r"\s*/\s*", "/", s)
    return s


def answer_strings(exercise) -> list[str]:
    """Строки, которые считаются «готовым ответом» на задание. Ответ ИИ не получает, а мы его ищем в ответе."""
    if exercise is None:
        return []
    ans = exercise.answer or {}
    payload = exercise.payload or {}
    out: list[str] = []
    if ans.get("value") not in (None, ""):
        out.append(ans["value"])
    out += list(ans.get("accept") or [])
    if ans.get("correct"):
        opts = {o.get("id"): o.get("text") for o in payload.get("options") or [] if isinstance(o, dict)}
        out += [opts[c] for c in ans["correct"] if opts.get(c)]
    steps = ans.get("steps") or []
    if steps and isinstance(steps[-1], dict) and steps[-1].get("answer") not in (None, ""):
        out.append(steps[-1]["answer"])
    prompt = _norm_answer(payload.get("prompt", ""))
    res = []
    for a in out:
        a = _norm_answer(a)
        if not a or a in res:
            continue
        # если ответ уже стоит в условии (например, «сравни 3/8 и 5/8»), проверить его невозможно — пропускаем
        if re.search(r"(?<![\w/])" + re.escape(a) + r"(?![\w/])", prompt):
            continue
        res.append(a)
    return res


def leaks_answer(text: str, exercise) -> bool:
    t = _norm_answer(text)
    for a in answer_strings(exercise):
        if re.search(r"(?<![\w/.,])" + re.escape(a) + r"(?![\w/]|[.,]\d)", t):
            return True
    return False
