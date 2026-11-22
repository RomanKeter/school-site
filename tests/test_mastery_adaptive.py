"""Mastery (раздел 7) и подстройка сложности (улучшение №2)."""
from apps.learning import adaptive as ad
from apps.learning import mastery as m


def win(weights_days):
    return [[w, d] for w, d in weights_days]


def test_weights():
    assert [m.weight(q) for q in (5, 4, 3, 2, 1, 0)] == [1.0, 1.0, 0.7, 0.4, 0.0, 0.0]


def test_window_is_last_10():
    w = []
    for i in range(15):
        w = m.push(w, 5 if i < 5 else 1, "2026-01-01")
    assert len(w) == 10
    assert m.mastery_value(w) == 0.0


def test_status_not_started_and_placed():
    assert m.status([]) == "not_started"
    assert m.status([], placed=True) == "almost"


def test_mastered_requires_80_8_answers_2_days():
    eight_one_day = win([(1.0, "d1")] * 8)
    assert m.status(eight_one_day) == "almost"  # 1 день — ещё не «Освоен»
    two_days = win([(1.0, "d1")] * 4 + [(1.0, "d2")] * 4)
    assert m.status(two_days) == "mastered"
    seven = win([(1.0, "d1")] * 4 + [(1.0, "d2")] * 3)
    assert m.status(seven) == "almost"  # N < 8


def test_threshold_exactly_80_percent():
    # 8 ответов: 6 по 1.0 и 2 по 0.4 → (6 + 0.8)/8 = 0.85 → освоен
    w = win([(1.0, "d1")] * 3 + [(1.0, "d2")] * 3 + [(0.4, "d2")] * 2)
    assert m.status(w) == "mastered"
    # 10 ответов: 8 по 1.0 + 2 по 0.0 → 0.8 ровно → освоен
    w = win([(1.0, "d1")] * 4 + [(1.0, "d2")] * 4 + [(0.0, "d2")] * 2)
    assert m.mastery_value(w) == 0.8
    assert m.status(w) == "mastered"
    # 0.79 → почти
    w = win([(1.0, "d1")] * 7 + [(0.9, "d2")] + [(0.0, "d2")] * 2)
    assert m.status(w) == "almost"


def test_learning_and_almost():
    assert m.status(win([(1.0, "d1")] * 5)) == "learning"  # N < 6
    assert m.status(win([(0.7, "d1")] * 6)) == "almost"
    assert m.status(win([(0.4, "d1")] * 6)) == "learning"


def test_refresh_after_two_failed_reviews():
    w = win([(1.0, "d1")] * 4 + [(1.0, "d2")] * 4)
    assert m.status(w, ever_mastered=True, review_fail_streak=2) == "refresh"
    assert m.status(w, ever_mastered=True, review_fail_streak=1) == "mastered"


def test_unlock_rule():
    assert m.is_unlocked(["almost", "mastered"])
    assert not m.is_unlocked(["learning"])
    assert m.is_unlocked([])


def test_frustration_rule():
    low = win([(0.0, "d1")] * 6)
    assert m.is_frustrated(low, 3)
    assert not m.is_frustrated(low, 2)


# ---- адаптивность ----

def test_three_right_raise_level():
    s = ad.AdaptiveState()
    for _ in range(2):
        s = ad.update(s, True)
    assert s.level == 1
    s = ad.update(s, True)
    assert s.level == 2 and s.right_streak == 0


def test_two_wrong_lower_level():
    s = ad.AdaptiveState(level=3)
    s = ad.update(s, False)
    assert s.level == 3
    s = ad.update(s, False)
    assert s.level == 2


def test_mixed_resets_streaks():
    s = ad.AdaptiveState(level=2)
    s = ad.update(s, True)
    s = ad.update(s, True)
    s = ad.update(s, False)  # серия верных обрывается
    s = ad.update(s, True)
    assert s.level == 2 and s.right_streak == 1 and s.wrong_streak == 0


def test_level_bounds():
    s = ad.AdaptiveState(level=3)
    for _ in range(3):
        s = ad.update(s, True)
    assert s.level == 3
    s = ad.AdaptiveState(level=1)
    for _ in range(4):
        s = ad.update(s, False)
    assert s.level == 1


def test_pick_difficulty_nearest():
    assert ad.pick_difficulty({1, 3}, 2) == 1
    assert ad.pick_difficulty({2, 3}, 1) == 2
    assert ad.pick_difficulty(set(), 1) is None
