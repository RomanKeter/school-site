"""Помощники генератора контента по белорусскому языку (D-800). Переиспользуют _ru_lib; меняются только
код предмета, подписи на белорусском и голос диктовки be-BY."""
import _ru_lib as R
from _ru_lib import CAT, NUM, skill, topic, write  # noqa: F401

ZERO = R.ZERO  # вариант «нічога не пішам»


def _be_zero(ex):
    for o in ex["payload"].get("options", []):
        if o["id"] == ZERO:
            o["text"] = "нічога"
    return ex


def FL(gap, right, wrong, explain, hint=None, prompt="Устаў прапушчаную літару"):
    return _be_zero(R.FL(gap, right, wrong, explain, hint, prompt))


def SC(prompt, right, wrong, explain, hint=None):
    return R.SC(prompt, right, wrong, explain, hint)


def PU(sentence, commas, explain, hint=None, prompt="Пастаў коскі: націсні на месца паміж словамі"):
    return R.PU(sentence, commas, explain, hint, prompt)


def DI(text, explain, prompt="Паслухай і запішы"):
    ex = R.DI(text, explain, prompt)
    ex["payload"]["lang"] = "be-BY"
    ex["payload"]["hints"] = [{"level": 1, "text": "Націсні «Медленно» і пішы па адным слове."}]
    return ex


def unit(key, title, order, quarter, topics):
    u = R.unit(key, title, order, quarter, topics)
    u["subject"] = "by"
    return u
