"""Помощники генератора контента по русскому языку (D-200, D-206). Ключи заданий: <префикс>.ex<N>."""
import json

ZERO = "0"  # вариант «ничего не пишем» (ь не нужен, буква не пишется)


def _opts(vals):
    return [{"id": v, "text": ("ничего" if v == ZERO else v)} for v in vals]


def FL(gap, right, wrong, explain, hint=None, prompt="Вставь пропущенную букву"):
    """fill_letters: gap — слово/фраза с «_» на месте пропуска."""
    before, after = gap.split("_", 1)
    wrong = [wrong] if isinstance(wrong, str) else list(wrong)
    opts = [right] + wrong
    opts.sort()
    return {"type": "fill_letters", "est_seconds": 25,
            "payload": {"prompt": prompt, "parts": [before, after], "options": _opts(opts),
                        "explain": explain, "hints": [{"level": 1, "text": hint}] if hint else []},
            "answer": {"correct": [right]}}


def SC(prompt, right, wrong, explain, hint=None):
    opts = [right] + list(wrong)
    return {"type": "single_choice", "est_seconds": 30,
            "payload": {"prompt": prompt, "options": [{"id": f"o{i}", "text": t} for i, t in enumerate(opts)],
                        "explain": explain, "hints": [{"level": 1, "text": hint}] if hint else []},
            "answer": {"correct": ["o0"]}}


def NUM(prompt, value, explain, hint=None):
    return {"type": "number_input", "est_seconds": 30,
            "payload": {"prompt": prompt, "explain": explain, "hints": [{"level": 1, "text": hint}] if hint else []},
            "answer": {"value": value}}


def CAT(prompt, buckets, explain, hint=None):
    items, ans, bl = [], {}, []
    for i, (title, words) in enumerate(buckets.items()):
        bid = f"b{i}"
        bl.append({"id": bid, "title": title})
        ans[bid] = list(words)
        items += [{"id": w, "text": w} for w in words]
    items.sort(key=lambda x: x["text"].lower())
    return {"type": "categorize", "est_seconds": 60,
            "payload": {"prompt": prompt, "items": items, "buckets": bl, "explain": explain,
                        "hints": [{"level": 1, "text": hint}] if hint else []},
            "answer": {"buckets": ans}}


def PU(sentence, commas, explain, hint=None, prompt="Поставь запятые: нажми на место между словами"):
    return {"type": "punctuation", "est_seconds": 45,
            "payload": {"prompt": prompt, "words": sentence.split(), "explain": explain,
                        "hints": [{"level": 1, "text": hint}] if hint else []},
            "answer": {"commas": list(commas)}}


def TILES(prompt, word, explain):
    return {"type": "letter_tiles", "est_seconds": 40,
            "payload": {"prompt": prompt, "letters": list(word), "explain": explain,
                        "hints": [{"level": 1, "text": f"В слове {len(word)} букв. Первая — «{word[0]}»."}]},
            "answer": {"value": word}}


def MO(word, labels, zero, explain, prompt="Разбери слово по составу"):
    """labels: по букве на каждую букву слова — p приставка, k корень, s суффикс, o окончание."""
    assert len(word) == len(labels), (word, labels)
    return {"type": "morphemes", "est_seconds": 60,
            "payload": {"prompt": prompt, "word": word, "explain": explain,
                        "hints": [{"level": 1, "text": "Начни с окончания: измени слово. Потом найди корень по однокоренным словам."}]},
            "answer": {"labels": labels, "zero": zero}}


def DI(text, explain, prompt="Послушай и запиши"):
    return {"type": "dictation", "est_seconds": 60,
            "payload": {"prompt": prompt, "say": text, "explain": explain,
                        "hints": [{"level": 1, "text": "Нажми «Медленно» и пиши по одному слову."}]},
            "answer": {"value": text}}


def skill(key, prefix, title, rule, ex_title, steps, exercises, prereq=(), hint=None):
    n = len(exercises)
    out = []
    for i, e in enumerate(exercises, 1):
        e = dict(e)
        e["key"] = f"{prefix}.ex{i}"
        e.setdefault("difficulty", 1 if i <= n / 3 else (2 if i <= 2 * n / 3 else 3))
        p = e["payload"]
        if not p.get("hints") and hint:
            p["hints"] = [{"level": 1, "text": hint}]
        p.setdefault("solution_steps", [p["explain"]])
        out.append(e)
    return {"key": key, "title": title, "rule_card": rule,
            "worked_example": {"title": ex_title, "steps": steps},
            "prerequisites": list(prereq), "exercises": out}


def unit(key, title, order, quarter, topics):
    return {"format_version": 1, "subject": "ru",
            "unit": {"key": key, "title": title, "grade": 5, "quarter": quarter, "order": order}, "topics": topics}


def topic(key, title, skills, synonyms=(), keywords=(), badge_code=None):
    t = {"key": key, "title": title, "synonyms": list(synonyms), "keywords": list(keywords), "skills": skills}
    if badge_code:
        t["badge_code"] = badge_code
    return t


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return sum(len(s["exercises"]) for t in data["topics"] for s in t["skills"])
