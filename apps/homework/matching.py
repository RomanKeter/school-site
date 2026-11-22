"""Подбор практики по тексту домашки без ИИ (FR-HW-2, D-301).

Каталог маленький (десятки навыков), поэтому поиск сделан на Python и одинаково работает на SQLite и PostgreSQL:
нормализация (регистр, ё→е), отбрасывание служебных слов, сравнение слов по общему началу (русские окончания)
и по триграммам (опечатки), отдельная обработка «§ 18». Цели поиска — навыки (практика заданиями)
и словарные темы английского (практика словами).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from apps.content.models import Skill, Topic

THRESHOLD = 0.6  # уверенность, начиная с которой показываем тему (FR-HW-2)
NEAR = 0.15  # показываем до 3 тем не хуже лучшей на эту величину

STOP = {
    "что", "задали", "задал", "задала", "нам", "мне", "на", "по", "про", "и", "в", "во", "с", "со", "к", "о", "об",
    "у", "из", "за", "для", "до", "а", "но", "или", "как", "это", "такое", "тема", "тему", "темы", "правило",
    "правила", "урок", "уроке", "домашка", "домашку", "домашнее", "задание", "задания", "дз", "учить", "выучить",
    "повторить", "надо", "нужно", "сделать", "делать", "читать", "прочитать", "мы", "я", "ты", "все", "всё", "еще", "ещё",
    "the", "a", "an", "to", "and", "of", "номер", "стр", "страница", "странице", "слова", "слов", "решать", "учим",
    "английский", "английскому", "английского", "математика", "математике", "математики", "english",
    "words", "word", "about", "my", "learn", "реши", "решить", "найди", "найти", "вычисли", "сколько", "чему",
    "равно", "равен", "будет",
}
REF_WORDS = {"параграф": "§", "пар": "§", "п": "§", "§": "§"}
NUM_WORDS = {"упражнение": "упр", "упр": "упр", "номер": "№", "№": "№"}


def norm(text: str) -> str:
    t = (text or "").lower().replace("ё", "е")
    t = t.replace("§", " § ").replace("№", " № ")
    t = re.sub(r"(\d+)", r" \1 ", t)
    return re.sub(r"[^\w§№]+", " ", t).strip()


def tokens(text: str) -> list[str]:
    out = []
    for w in norm(text).split():
        w = REF_WORDS.get(w, NUM_WORDS.get(w, w))
        if w in STOP:
            continue
        out.append(w)
    return out


def _tri(w: str) -> set[str]:
    w = f"  {w} "
    return {w[i:i + 3] for i in range(len(w) - 2)}


def tok_sim(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if a.isdigit() or b.isdigit() or len(a) < 3 or len(b) < 3:
        return 0.0
    cp = 0
    for x, y in zip(a, b):
        if x != y:
            break
        cp += 1
    if cp >= 4 and cp >= min(len(a), len(b)) - 3:
        return 0.95  # одно слово в разных формах: «дроби/дробей/дробь»
    if max(len(a), len(b)) <= 4 and cp >= 2 and cp >= min(len(a), len(b)) - 1:
        return 0.85  # короткие слова: «еда/еду»
    ta, tb = _tri(a), _tri(b)
    j = len(ta & tb) / len(ta | tb)
    return j if j >= 0.45 else 0.0  # опечатки: «знамнатель» ~ «знаменатель»


def phrase_score(q: list[str], p: list[str]) -> float:
    if not q or not p:
        return 0.0
    q_best = [max(tok_sim(a, b) for b in p) for a in q]
    p_best = [max(tok_sim(a, b) for a in q) for b in p]
    q_cov = sum(q_best) / len(q)
    p_cov = sum(p_best) / len(p)
    return 0.75 * q_cov + 0.25 * p_cov


@dataclass
class Target:
    kind: str  # skill | words
    id: int
    title: str
    subject: str
    phrases: list = field(default_factory=list)  # [(tokens, weight)]


def catalog(subject_code: str | None = None) -> list[Target]:
    out = []
    skills = Skill.objects.filter(status="published").select_related("topic__unit__subject")
    if subject_code:
        skills = skills.filter(topic__unit__subject__code=subject_code)
    for s in skills:
        if not s.exercises.filter(status="published").exists():
            continue
        t = s.topic
        ph = [(s.title, 1.0), (t.title, 0.85)]
        ph += [(x, 0.85) for x in (t.synonyms or []) + (t.keywords or [])]
        ph += [(x, 0.9) for x in t.textbook_refs or []]
        alias = getattr(s, "hw_alias", None)
        ph += [(x, 1.0) for x in (alias.phrases if alias else [])]
        out.append(Target("skill", s.id, s.title, t.unit.subject.code, [(tokens(x), w) for x, w in ph]))
    topics = Topic.objects.filter(status="published", words__isnull=False).distinct().select_related("unit__subject")
    if subject_code:
        topics = topics.filter(unit__subject__code=subject_code)
    for t in topics:
        ph = [(t.title, 1.0)]
        alias = getattr(t, "hw_alias", None)
        ph += [(x, 1.0) for x in (alias.phrases if alias else [])]
        for w in t.words.filter(status="published"):
            ph += [(w.word, 0.85), (w.translation_ru, 0.85)]
        out.append(Target("words", t.id, f"Слова: {t.title}", t.unit.subject.code, [(tokens(x), w) for x, w in ph]))
    return out


def search(text: str, subject_code: str | None = None) -> list[dict]:
    """[{"kind", "id", "title", "subject", "score"}] — до 3 уверенных совпадений, лучшее первым."""
    shape = _shape_words(text)
    q = tokens(text)
    if shape:  # условие задачи: числа из него теме не помогают
        q = [w for w in q if not w.isdigit()] + shape
    if not q:
        return []
    scored = []
    for t in catalog(subject_code):
        best = max((phrase_score(q, p) * w for p, w in t.phrases if p), default=0.0)
        scored.append((round(best, 3), t))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] < THRESHOLD:
        return []
    top = scored[0][0]
    return [{"kind": t.kind, "id": t.id, "title": t.title, "subject": t.subject, "score": s}
            for s, t in scored[:3] if s >= THRESHOLD and s >= top - NEAR]


def _shape_words(text: str) -> list[str]:
    """Если ребёнок вставил условие («2/7 + 3/7», «x + 37 = 105»), тему подсказывает вид записи."""
    t = (text or "").lower()
    extra = []
    if re.search(r"\d+\s*/\s*\d+", t):
        extra.append("дроби")
    if re.search(r"(?<![a-zа-я])[xх](?![a-zа-я])", t) and "=" in t:
        extra.append("уравнения")
    return extra


_TASK_RX = [
    re.compile(r"\d+\s*[-+*/:×·=<>]\s*\d+"),  # 2/7 + 3/7, 48 : 6, x + 37 = 105
    re.compile(r"(?i)\b(реши|решить|найди|найти|вычисли|вычислить|сколько|чему равн|translate|переведи)\w*\b.*\d"),
    re.compile(r"(?i)\b(реши|решить|найди|вычисли|сколько|переведи)\w*\b.{25,}"),
]


def looks_like_task(text: str) -> bool:
    """FR-HW-5: ребёнок вставил условие задачи, а не тему. Ссылки «§ 18», «упр. 145» задачей не считаются."""
    return any(rx.search(text or "") for rx in _TASK_RX)
