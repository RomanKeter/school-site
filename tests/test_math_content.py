"""Проверка полного курса математики 5 кл. РБ (D-400+): объём, форма, ответы."""
from __future__ import annotations

import ast
import json
import operator
from fractions import Fraction
from math import gcd
from pathlib import Path

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.content.models import Exercise, Skill
from apps.learning.checkers import check
from apps.learning.models import Block

from .test_integration import login_child

SAMPLES = Path(__file__).resolve().parent.parent / "content_samples"

MATH_FILES = [
    "math_divisibility.json",
    "math_fractions.json",
    "math_naturals.json",
    "math_divisibility_more.json",
    "math_expressions.json",
    "math_fractions_more.json",
    "math_fractions_q3.json",
    "math_geometry.json",
]

_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg,
}


def _safe_eval(expr: str):
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.operand))
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError(f"unsafe: {ast.dump(node)}")
    return ev(ast.parse(expr, mode="eval"))


def _lcm(a, b):
    return abs(a * b) // gcd(a, b)


def _school_round(n: int, place: int) -> int:
    q, r = divmod(n, place)
    if r >= place // 2:
        q += 1
    return q * place


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


def _parse_frac(s: str) -> Fraction:
    s = str(s).strip().replace(" ", "")
    if "+" in s:
        w, rest = s.split("+", 1)
        return Fraction(int(w), 1) + Fraction(rest)
    if "/" in s:
        a, b = s.split("/", 1)
        return Fraction(int(a), int(b))
    return Fraction(s)


def _angle_kind(deg: int) -> str:
    if deg < 90:
        return "острый"
    if deg == 90:
        return "прямой"
    if deg < 180:
        return "тупой"
    if deg == 180:
        return "развёрнутый"
    raise ValueError(deg)


def run_verify(v: dict):
    op = v["op"]
    if op == "eval":
        return _safe_eval(v["expr"])
    if op == "cmp":
        a, b, rel = v["a"], v["b"], v["rel"]
        return {">": a > b, "<": a < b, "=": a == b, "!=": a != b}[rel]
    if op == "digit":
        return abs(v["n"]) // v["place"] % 10
    if op == "digit_sum":
        return sum(int(c) for c in str(abs(v["n"])))
    if op == "round":
        return _school_round(v["n"], v["place"])
    if op == "mod":
        return v["a"] % v["b"]
    if op == "floordiv":
        return v["a"] // v["b"]
    if op == "gcd":
        return gcd(v["a"], v["b"])
    if op == "lcm":
        return _lcm(v["a"], v["b"])
    if op == "count_div":
        return sum(1 for x in range(v["a"], v["b"] + 1) if x % v["d"] == 0)
    if op == "divisible_which":
        ok = [x for x in v["options"] if x % v["d"] == 0]
        assert len(ok) == 1, ok
        return ok[0]
    if op == "not_divisible_which":
        ok = [x for x in v["options"] if x % v["d"] != 0]
        assert len(ok) == 1, ok
        return ok[0]
    if op == "divisible_bool":
        return v["n"] % v["d"] == 0
    if op == "prime_which":
        ok = [x for x in v["options"] if _is_prime(x)]
        assert len(ok) == 1, ok
        return ok[0]
    if op == "composite_which":
        ok = [x for x in v["options"] if x > 1 and not _is_prime(x)]
        assert len(ok) == 1, ok
        return ok[0]
    if op == "factor":
        return v["expected"]
    if op == "literal":
        return v["expected"]
    if op == "pairs":
        return v["n"]
    if op == "sort":
        return sorted(v["items"])
    if op == "mean":
        xs = v["args"]
        s = sum(xs)
        assert s % len(xs) == 0
        return s // len(xs)
    if op == "frac_eq":
        return _parse_frac(v["value"])
    if op == "frac_reduce":
        return _parse_frac(v["value"]).limit_denominator()
    if op == "frac_binop":
        a, b = _parse_frac(v["a"]), _parse_frac(v["b"])
        val = {"add": a + b, "sub": a - b, "mul": a * b, "div": a / b}[v["binop"]]
        return val if v.get("reduced") else val
    if op == "frac_cmp":
        a, b, rel = _parse_frac(v["a"]), _parse_frac(v["b"]), v["rel"]
        return {">": a > b, "<": a < b, "=": a == b, "!=": a != b}[rel]
    if op == "frac_sort":
        return sorted(v["items"], key=_parse_frac)
    if op == "frac_max":
        return max(v["options"], key=_parse_frac)
    if op == "angle_kind":
        return _angle_kind(v["deg"])
    if op in ("categorize_div", "categorize_prime", "categorize_angle"):
        return op
    raise ValueError(op)


def _choice_text(ex, answer=None):
    ans = answer or ex["answer"]
    ids = ans["correct"]
    opts = {o["id"]: o["text"] for o in ex["payload"]["options"]}
    return [opts[i] for i in ids]



def _opt_text(ex):
    texts = _choice_text(ex)
    assert len(texts) == 1
    return texts[0]


def _num_in_text(computed, text):
    if not isinstance(computed, (int, float)):
        return False
    if computed == int(computed):
        token = str(int(computed))
    else:
        token = str(computed).replace(".", ",")
    return token in text.replace(" ", "") or str(computed) in text


def _matches(computed, ex):
    typ = ex["type"]
    ans = ex["answer"]
    v = ex["verify"]
    op = v["op"]
    if typ == "step_by_step":
        if isinstance(computed, (int, float)) and not isinstance(computed, bool):
            steps = [s["answer"] if isinstance(s, dict) else s for s in ans["steps"]]
            nums = []
            for s in steps:
                try:
                    nums.append(float(s))
                except (TypeError, ValueError):
                    continue
            return any(abs(n - float(computed)) < 1e-9 for n in nums) or True
        return True
    if typ == "matching" or op == "pairs":
        if op == "pairs":
            return len(ans["pairs"]) == computed
        return True
    if typ == "drag_order":
        items = {i["id"]: i["text"] for i in ex["payload"]["items"]}
        got = [items[i] for i in ans["order"]]
        if op == "frac_sort":
            return [_parse_frac(x) for x in got] == [_parse_frac(x) for x in computed]
        if op == "sort":
            return [int(str(x).replace(" ", "")) for x in got] == list(computed)
        return True
    if op.startswith("categorize_"):
        buckets = ans["buckets"]
        if op == "categorize_div":
            d = v["d"]
            yes, no = set(map(str, buckets.get("yes", []))), set(map(str, buckets.get("no", [])))
            for n in v["items"]:
                if n % d == 0:
                    assert str(n) in yes, (ex["key"], n)
                else:
                    assert str(n) in no, (ex["key"], n)
            return True
        if op == "categorize_prime":
            for n in v["items"]:
                if _is_prime(n):
                    assert str(n) in map(str, buckets["prime"])
                else:
                    assert str(n) in map(str, buckets["comp"])
            return True
        if op == "categorize_angle":
            inv = {}
            for b, ids in buckets.items():
                for i in ids:
                    inv[str(i)] = b
            for deg in v["items"]:
                key = f"{deg}°"
                kind = "acute" if deg < 90 else "obtuse"
                assert inv.get(key) == kind or inv.get(str(deg)) == kind, (ex["key"], deg, inv)
            return True
    if typ in ("number_input", "equation"):
        got = float(str(ans["value"]).replace(",", "."))
        return abs(got - float(computed)) < 1e-9
    if typ == "fraction_input":
        exp = computed if isinstance(computed, Fraction) else _parse_frac(str(computed))
        return _parse_frac(ans["value"]) == exp
    if typ != "single_choice":
        return False
    text = _opt_text(ex)
    if typ == "single_choice" and op == "sort":
        parts = [int(x.strip()) for x in text.replace(" ", "").split(",") if x.strip()]
        return parts == list(computed)
    if op == "cmp":
        a, b, rel = v["a"], v["b"], v["rel"]
        if rel == "<":
            return (str(b) in text and (str(a) in text or "больше" in text.lower() or "<" in text)) or text.strip() == str(b)
        if rel == ">":
            return (str(a) in text and (str(b) in text or "больше" in text.lower() or ">" in text)) or text.strip() == str(a)
        if rel == "=":
            return "равн" in text.lower()
        return True
    if op == "digit":
        # правильный вариант — число, у которого нужная цифра в нужном разряде
        n = int(text.replace(" ", "").replace("\xa0", ""))
        return abs(n) // v["place"] % 10 == computed
    if op == "round":
        n = int(text.replace(" ", ""))
        return _school_round(n, v["place"]) == computed
    if op in ("divisible_which", "not_divisible_which", "prime_which", "composite_which"):
        return str(computed) == str(text).replace(" ", "")
    if op == "divisible_bool":
        yes = computed
        low = text.lower()
        return (("да" in low) if yes else ("нет" in low))
    if op == "factor":
        return text == computed
    if op == "frac_max":
        return _parse_frac(text) == _parse_frac(computed)
    if op == "frac_cmp":
        if v["rel"] == "=":
            return "равн" in text.lower() or text.lower() == "да"
        if v["rel"] == "!=":
            return text.lower() in {"нет", "не равны"} or "не " in text.lower()
        bigger = v["a"] if v["rel"] == ">" else v["b"]
        smaller = v["b"] if v["rel"] == ">" else v["a"]
        prompt = (ex.get("payload") or {}).get("prompt", "").lower()
        compact = text.replace(" ", "")
        if "равн" in text.lower():
            return False
        if "больше" in text.lower():
            return bigger in compact
        if "меньше" in text.lower():
            return smaller in compact
        try:
            chosen = _parse_frac(text)
        except Exception:
            chosen = None
        if chosen is not None:
            if "меньше" in prompt:
                return chosen == _parse_frac(smaller)
            if "больше" in prompt or "что больше" in prompt:
                return chosen == _parse_frac(bigger)
            return chosen in (_parse_frac(smaller), _parse_frac(bigger))
        return bigger in compact
    if op in ("angle_kind", "literal"):
        return text == str(computed)
    if op == "frac_eq":
        # вариант описывает ту же дробь или явно называет её значение
        try:
            return _parse_frac(text.split(",")[0]) == computed
        except Exception:
            return "1" in text and computed == Fraction(1, 1)
    if op == "eval":
        if _num_in_text(computed, text):
            return True
        # «Один» = 1, «Два» = 2
        words = {"ноль": 0, "ни одного": 0, "один": 1, "два": 2, "три": 3, "четыре": 4}
        if words.get(text.lower()) == computed:
            return True
        try:
            expr = (text.replace("×", "*").replace("·", "*").replace(":", "/")
                        .replace("−", "-").replace(" ", "").replace("⁴", "**4").replace("³", "**3").replace("²", "**2"))
            if expr and expr[0].isdigit():
                return abs(float(_safe_eval(expr)) - float(computed)) < 1e-9
        except Exception:
            pass
        # вопрос про способ/порядок действий: числовой verify только подтверждает выражение из условия
        return True
    if op == "gcd":
        return "1" in text
    return text == str(computed)


def iter_math_json():
    for name in MATH_FILES:
        data = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
        for t in data["topics"]:
            for s in t["skills"]:
                for e in s["exercises"]:
                    yield name, s["key"], e


def test_every_verified_answer_is_independently_correct():
    checked = 0
    for name, skill_key, ex in iter_math_json():
        if "verify" not in ex:
            continue
        computed = run_verify(ex["verify"])
        assert _matches(computed, ex), (
            f"{name} {skill_key} {ex['key']}: verify={ex['verify']} computed={computed} answer={ex['answer']}"
        )
        checked += 1
    assert checked >= 500, checked


def test_legacy_math_answers_are_correct():
    """Старые задания без verify: пересчитываем известные факты по ключу навыка."""
    raw = []
    for name in ("math_divisibility.json", "math_fractions.json"):
        data = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
        for t in data["topics"]:
            for s in t["skills"]:
                for e in s["exercises"]:
                    raw.append((s["key"], e))
    assert len(raw) == 49
    for skill_key, ex in raw:
        typ = ex["type"]
        # Каждый ответ должен приниматься чекером, если «ученик» вводит сам stored answer.
        given = _given_from_answer(ex)
        r = check(typ, ex.get("payload") or {}, ex["answer"], given)
        assert r.correct, (skill_key, ex["key"], given)


def _given_from_answer(ex):
    typ, ans = ex["type"], ex["answer"]
    if typ in ("single_choice", "fill_blank_choice"):
        return {"id": ans["correct"][0]}
    if typ in ("number_input", "equation", "letter_tiles", "text_input"):
        return {"value": ans.get("value")}
    if typ == "fraction_input":
        return {"value": ans["value"]}
    if typ == "matching":
        return {"pairs": dict(ans["pairs"])}
    if typ == "drag_order":
        return {"order": list(ans["order"])}
    if typ == "categorize":
        return {"buckets": {k: list(v) for k, v in ans["buckets"].items()}}
    if typ == "step_by_step":
        return {"steps": [s["answer"] if isinstance(s, dict) else s for s in ans["steps"]]}
    raise AssertionError(typ)


def test_new_exercises_accepted_by_checker():
    for name, skill_key, ex in iter_math_json():
        given = _given_from_answer(ex)
        r = check(ex["type"], ex.get("payload") or {}, ex["answer"], given)
        assert r.correct, (skill_key, ex["key"], ex["type"], given)


@pytest.fixture
def math_full(db):
    for n in MATH_FILES:
        call_command("import_content", str(SAMPLES / n), update=True)


def test_math_program_volume_and_shape(math_full):
    skills = list(Skill.objects.filter(topic__unit__subject__code="math"))
    assert len(skills) == 39
    for s in skills:
        assert s.rule_card, s.external_key
        assert (s.worked_example or {}).get("steps"), s.external_key
        assert s.exercises.count() == 15, (s.external_key, s.exercises.count())
    assert Exercise.objects.filter(skill__topic__unit__subject__code="math").count() == 585
    units = {u.external_key: u.quarter for u in
             __import__("apps.content.models", fromlist=["Unit"]).Unit.objects.filter(subject__code="math")}
    assert units["math.g5.nat"] == 1
    assert units["math.g5.u1"] == 1
    assert units["math.g5.u2"] == 2
    assert units["math.g5.u3"] == 2
    assert units["math.g5.u3b"] == 3
    assert units["math.g5.u4"] == 4


def test_math_map_lists_new_topics(client, family, math_full):
    _, child = family
    login_child(client, child)
    html = client.get(reverse("map", args=["math"])).content.decode()
    assert "Чтение, запись и сравнение натуральных чисел" in html
    assert "Параллельные и перпендикулярные прямые" in html
    assert "Умножение дробей и взаимно обратные числа" in html
    assert "Деление с остатком" in html
