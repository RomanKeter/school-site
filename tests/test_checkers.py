from apps.learning.checkers import check, normalize_text


def test_normalize():
    assert normalize_text("  Ёжик ") == "ежик"
    assert normalize_text("3,5") == "3.5"


def test_choice():
    assert check("single_choice", {}, {"correct": ["a"]}, {"id": "a"}).correct
    assert not check("single_choice", {}, {"correct": ["a"]}, {"id": "b"}).correct


def test_number_tolerance_and_comma():
    assert check("number_input", {}, {"value": "2.5"}, {"value": "2,5"}).correct
    assert check("equation", {}, {"value": "68"}, {"value": " 68 "}).correct
    assert not check("number_input", {}, {"value": "68"}, {"value": "abc"}).correct


def test_fraction_equivalence_and_distractor():
    p = {"distractor_feedback": {"5/14": "Ты сложила знаменатели"}}
    assert check("fraction_input", p, {"value": "5/7"}, {"num": "5", "den": "7"}).correct
    assert check("fraction_input", p, {"value": "1/2"}, {"num": "2", "den": "4"}).correct
    assert not check("fraction_input", p, {"value": "1/2", "require_reduced": True}, {"num": "2", "den": "4"}).correct
    r = check("fraction_input", p, {"value": "5/7"}, {"num": "5", "den": "14"})
    assert not r.correct and "знаменатели" in r.distractor


def test_matching_partial():
    a = {"pairs": {"l0": "r0", "l1": "r1"}}
    r = check("matching", {}, a, {"pairs": {"l0": "r0", "l1": "r0"}})
    assert not r.correct and r.partial == 0.5


def test_order_categorize_tiles_steps():
    assert check("drag_order", {}, {"order": ["a", "b"]}, {"order": ["a", "b"]}).correct
    a = {"buckets": {"p": ["2", "3"], "c": ["4"]}}
    assert check("categorize", {}, a, {"buckets": {"p": ["3", "2"], "c": ["4"]}}).correct
    assert check("categorize", {}, a, {"buckets": {"p": ["2"], "c": ["4", "3"]}}).partial == 2 / 3
    assert check("letter_tiles", {}, {"value": "apple"}, {"value": "Apple"}).correct
    st = {"steps": [{"answer": 36}, {"answer": 30}, {"answer": 66}]}
    assert check("step_by_step", {}, st, {"steps": ["36", "30", "66"]}).correct
    assert not check("step_by_step", {}, st, {"steps": ["36", "30", "65"]}).correct
