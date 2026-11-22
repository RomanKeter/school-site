"""Генератор контента по белорусскому языку, 5 класс (D-800). Запуск: python content_samples/build_by_samples.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _by_lib import write  # noqa: E402

OUT = Path(__file__).resolve().parent
PARTS = []
try:
    from _by_u0_u1 import U0, U1
    PARTS += [("by_text.json", U0), ("by_repeat.json", U1)]
    from _by_u2 import U2
    PARTS += [("by_syntax.json", U2)]
    from _by_u3 import U3
    PARTS += [("by_phonetics.json", U3)]
    from _by_u4_u5 import U4, U5
    PARTS += [("by_lexis.json", U4), ("by_dictation.json", U5)]
except ImportError as e:  # во время сборки по частям
    print("skip:", e)

if __name__ == "__main__":
    tot_s = tot_e = 0
    for name, data in PARTS:
        n = write(OUT / name, data)
        s = sum(len(t["skills"]) for t in data["topics"])
        tot_s += s; tot_e += n
        print(f"{name}: {s} навыков, {n} заданий")
    print(f"Итого: {tot_s} навыков, {tot_e} заданий")
