"""Серии дней (GAM-8…GAM-11)."""
from __future__ import annotations

import datetime as dt

from .models import Streak


def get(child) -> Streak:
    obj, _ = Streak.objects.get_or_create(child=child)
    return obj


def on_mission_done(child, today: dt.date) -> tuple[Streak, bool]:
    """Вернуть (streak, comeback). comeback — перерыв ≥ 3 дня."""
    s = get(child)
    # начисление заморозки в понедельник
    week = today.isocalendar()[1]
    if s.freezes_week != week and today.weekday() == 0:
        s.freezes_available = min(2, s.freezes_available + 1)
        s.freezes_week = week

    comeback = False
    if s.last_counted_date == today:
        return s, False
    if s.last_counted_date:
        gap = (today - s.last_counted_date).days
        # дни off не прерывают — упрощённо: считаем календарные; parent days_off вычитаем
        off = set(child.settings.days_off or [])
        real_gap = sum(1 for i in range(1, gap) if (s.last_counted_date + dt.timedelta(days=i)).weekday() not in off)
        if real_gap == 0:
            s.current += 1
        elif real_gap == 1 and s.freezes_available > 0:
            s.freezes_available -= 1
            s.current += 1
        else:
            if real_gap >= 3:
                comeback = True
            s.current = 1
    else:
        s.current = 1
    s.best = max(s.best, s.current)
    s.last_counted_date = today
    s.save()
    return s, comeback
