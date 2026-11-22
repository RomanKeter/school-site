"""Лимиты (раздел 9.6 ТЗ, D-104): вопросов в день, 1 запрос в N секунд, месячный бюджет."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone

from .models import AIQuery, AISettings

MSG_LIMIT = "На сегодня вопросы к Масе закончились. Загляни в карточку правила или спроси взрослых — завтра Мася снова поможет!"
MSG_RATE = "Мася ещё думает над прошлым вопросом. Подожди несколько секунд и спроси снова."
MSG_OFF = "Помощник сейчас выключен. Попробуй подсказку или спроси взрослых."


def _cfg():
    return getattr(settings, "AI", {}) or {}


def settings_for(child) -> AISettings:
    """Без записи в БД: если родитель ещё не открывал настройки — значения по умолчанию."""
    return AISettings.objects.filter(child=child).first() or AISettings(child=child)


def _day_range(child, day: dt.date):
    tz = ZoneInfo(child.family.timezone)
    start = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    return start, start + dt.timedelta(days=1)


def used_today(child, day: dt.date) -> float:
    start, end = _day_range(child, day)
    s = AIQuery.objects.filter(child=child, created_at__gte=start, created_at__lt=end).aggregate(s=Sum("units"))["s"]
    return float(s or 0)


def left_today(child, day: dt.date) -> float:
    return max(0.0, settings_for(child).daily_limit - used_today(child, day))


def check(child, day: dt.date, units: float = 1) -> str | None:
    """None — можно; иначе текст для ребёнка. Не меняет состояние."""
    if units > 0 and used_today(child, day) + units > settings_for(child).daily_limit + 1e-9:
        return MSG_LIMIT
    if cache.get(f"ai-rate-{child.pk}"):
        return MSG_RATE
    return None


def touch(child) -> None:
    sec = int(_cfg().get("MIN_INTERVAL_SECONDS", 10))
    if sec > 0:
        cache.set(f"ai-rate-{child.pk}", 1, sec)


def month_cost() -> Decimal:
    now = timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return AIQuery.objects.filter(created_at__gte=start).aggregate(s=Sum("cost_usd"))["s"] or Decimal("0")


def budget_exceeded() -> bool:
    """AI-3: при 100 % бюджета внешний ИИ выключается до 1-го числа (работает офлайн-режим)."""
    return month_cost() >= Decimal(str(_cfg().get("MONTHLY_BUDGET_USD", 3)))
