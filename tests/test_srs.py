"""Интервальное повторение (раздел 6, AC-1-06)."""
import datetime as dt

import pytest
from hypothesis import given, strategies as st

from apps.srs.algorithm import CardState, SrsParams, apply_fuzz, new_card, quality, schedule, update_ef
from apps.srs.interleave import interleave, max_run

D0 = dt.date(2026, 1, 1)


class ZeroRng:
    def uniform(self, a, b):
        return 0.0


class MaxRng:
    def uniform(self, a, b):
        return b


def day(n):
    return D0 + dt.timedelta(days=n)


def test_new_card_due_tomorrow():
    c = new_card(D0)
    assert (c.n, c.ef, c.interval, c.due) == (0, 2.5, 1, day(1))


def test_spec_example_table():
    """Пример расчёта из 6.3: apple, EF 2.5."""
    c = new_card(D0)
    c = schedule(c, 5, day(1), ZeroRng())
    assert (round(c.ef, 2), c.n, c.interval, c.due) == (2.6, 1, 3, day(4))
    c = schedule(c, 4, day(4), ZeroRng())
    assert (round(c.ef, 2), c.n, c.interval, c.due) == (2.6, 2, 7, day(11))
    c = schedule(c, 3, day(11), ZeroRng())
    assert (round(c.ef, 2), c.n, c.interval) == (2.46, 3, 17)
    assert c.due == day(28)
    c = schedule(c, 1, day(28), ZeroRng())
    assert (round(c.ef, 2), c.n, c.interval, c.due) == (1.92, 0, 1, day(29))
    assert c.lapses == 1
    c = schedule(c, 5, day(29), ZeroRng())
    assert (round(c.ef, 2), c.n, c.interval, c.due) == (2.02, 1, 3, day(32))


def test_accelerated_time_perfect_answers_1_3_7_18():
    """AC-1-06: 1 → 3 → 7 → ~18 для идеальных ответов, сброс на 1 при ошибке."""
    c = new_card(D0)
    intervals = [c.interval]
    today = c.due
    for _ in range(3):
        c = schedule(c, 5, today, ZeroRng())
        intervals.append(c.interval)
        today = c.due
    assert intervals[:3] == [1, 3, 7]
    assert 17 <= intervals[3] <= 20
    c = schedule(c, 2, today, ZeroRng())
    assert c.interval == 1 and c.n == 0


def test_ef_bounds():
    assert update_ef(1.3, 0) == 1.3
    assert update_ef(2.8, 5) == 2.8


def test_overdue_bonus_sr3():
    c = CardState(n=2, ef=2.5, interval=7, due=day(10))
    on_time = schedule(c, 5, day(10), ZeroRng())
    late = schedule(c, 5, day(20), ZeroRng())  # просрочено на 10 дней → база 7 + 5
    assert late.interval > on_time.interval
    assert late.interval == round(12 * 2.6)


def test_i_max_cap():
    c = CardState(n=5, ef=2.8, interval=50, due=day(0))
    assert schedule(c, 5, day(0), ZeroRng()).interval == 60


def test_fuzz_only_for_7_plus():
    assert apply_fuzz(3, MaxRng()) == 3
    assert apply_fuzz(20, MaxRng()) == 22
    assert apply_fuzz(20, None) == 20
    assert apply_fuzz(20, MaxRng(), SrsParams(fuzz_pct=0)) == 20


def test_q_out_of_range():
    with pytest.raises(ValueError):
        schedule(new_card(D0), 6, D0)


@pytest.mark.parametrize(
    "kw,q",
    [
        (dict(correct=True, attempt_no=1, hints_used=0, duration_s=10, est_seconds=40), 5),
        (dict(correct=True, attempt_no=1, hints_used=0, duration_s=100, est_seconds=40), 4),
        (dict(correct=True, attempt_no=2, hints_used=0, duration_s=10, est_seconds=40), 3),
        (dict(correct=True, attempt_no=1, hints_used=1, duration_s=10, est_seconds=40), 3),
        (dict(correct=True, attempt_no=1, hints_used=2, duration_s=10, est_seconds=40), 2),
        (dict(correct=True, attempt_no=3, hints_used=0, duration_s=10, est_seconds=40), 2),
        (dict(correct=False, attempt_no=3, hints_used=0, duration_s=10, est_seconds=40), 1),
        (dict(correct=False, attempt_no=1, hints_used=0, duration_s=1, est_seconds=40, skipped=True), 0),
    ],
)
def test_quality_table(kw, q):
    assert quality(**kw) == q


@given(
    qs=st.lists(st.integers(min_value=0, max_value=5), min_size=1, max_size=40),
    gaps=st.lists(st.integers(min_value=0, max_value=90), min_size=40, max_size=40),
    u=st.floats(min_value=-0.1, max_value=0.1),
)
def test_property_bounds(qs, gaps, u):
    """Свойства: 1 ≤ I ≤ I_max; EF ∈ [1.3; 2.8]."""

    class R:
        def uniform(self, a, b):
            return u

    c = new_card(D0)
    today = D0
    for q, g in zip(qs, gaps):
        today = today + dt.timedelta(days=g)
        c = schedule(c, q, today, R())
        assert 1 <= c.interval <= 60
        assert 1.3 <= c.ef <= 2.8
        assert c.due > today


def test_interleave_no_adjacent_same_group():
    items = [("a", i) for i in range(3)] + [("b", i) for i in range(3)] + [("c", i) for i in range(2)]
    out = interleave(items, key=lambda x: x[0])
    assert sorted(out) == sorted(items)
    assert max_run(out, key=lambda x: x[0]) == 1


def test_interleave_keeps_order_inside_group():
    items = [("a", 1), ("a", 2), ("b", 1), ("a", 3)]
    out = interleave(items, key=lambda x: x[0])
    assert [x for x in out if x[0] == "a"] == [("a", 1), ("a", 2), ("a", 3)]


def test_interleave_unavoidable_runs():
    items = [("a", i) for i in range(4)] + [("b", 0)]
    out = interleave(items, key=lambda x: x[0])
    assert max_run(out, key=lambda x: x[0]) <= 3


@given(st.lists(st.sampled_from("abcd"), max_size=30))
def test_interleave_property(keys):
    items = list(enumerate(keys))
    out = interleave(items, key=lambda x: x[1])
    assert sorted(out) == sorted(items)
    from collections import Counter

    cnt = Counter(keys)
    if cnt and max(cnt.values()) <= (len(keys) + 1) // 2:
        assert max_run(out, key=lambda x: x[1]) <= 1
