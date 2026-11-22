"""Interleaving (перемешивание задач) в повторении — принятое улучшение №4.

Задачи из разных навыков/предметов идут вперемешку: подряд не стоят две задачи одной
группы, если только этого можно избежать. Порядок приоритета внутри группы сохраняется.
"""
from collections import OrderedDict
from typing import Callable, Hashable, Iterable, TypeVar

T = TypeVar("T")


def interleave(items: Iterable[T], key: Callable[[T], Hashable]) -> list[T]:
    groups: "OrderedDict[Hashable, list[T]]" = OrderedDict()
    for it in items:
        groups.setdefault(key(it), []).append(it)
    result: list[T] = []
    last = object()
    while groups:
        # берём самую большую группу, отличную от предыдущей (жадный алгоритм без «слипаний»)
        candidates = [k for k in groups if k != last] or list(groups)
        k = max(candidates, key=lambda g: (len(groups[g]), -list(groups).index(g)))
        result.append(groups[k].pop(0))
        if not groups[k]:
            del groups[k]
        last = k
    return result


def max_run(items, key) -> int:
    """Длина самой длинной серии подряд идущих элементов одной группы (для тестов)."""
    best = run = 0
    prev = object()
    for it in items:
        k = key(it)
        run = run + 1 if k == prev else 1
        best = max(best, run)
        prev = k
    return best
