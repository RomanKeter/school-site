"""Звёзды (раздел 8.1). Потолок 80/день из заданий; уникальный ключ против двойного начисления."""
from __future__ import annotations

import datetime as dt

from django.db import IntegrityError, transaction
from django.db.models import Sum

from .models import StarTransaction

DAILY_CAP = 80
TASK_SOURCES = {"attempt", "review"}


def balance(child) -> int:
    return StarTransaction.objects.filter(child=child).aggregate(s=Sum("amount"))["s"] or 0


def earned_today(child, today: dt.date, *, task_only=False) -> int:
    qs = StarTransaction.objects.filter(child=child, day=today, amount__gt=0)
    if task_only:
        qs = qs.filter(source_type__in=TASK_SOURCES)
    return qs.aggregate(s=Sum("amount"))["s"] or 0


@transaction.atomic
def award(child, amount: int, source_type: str, source_id, today: dt.date) -> int:
    """Начислить звёзды. Возвращает фактически начисленное (0 при дубле/потолке)."""
    if amount <= 0:
        return 0
    if source_type in TASK_SOURCES:
        already = earned_today(child, today, task_only=True)
        if already >= DAILY_CAP:
            return 0
        amount = min(amount, DAILY_CAP - already)
    try:
        StarTransaction.objects.create(
            child=child, amount=amount, source_type=source_type,
            source_id=str(source_id), day=today,
        )
    except IntegrityError:
        return 0
    return amount
