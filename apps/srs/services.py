import datetime as dt

from django.db import transaction

from .algorithm import SrsParams, default_rng, new_card, schedule
from .models import ReviewItem, ReviewLog, SrsConfig


def params():
    cfg = SrsConfig.objects.filter(is_active=True).first()
    return cfg.to_params() if cfg else SrsParams.from_settings()


def ensure_item(child, *, today, skill=None, word=None, exercise=None, due_tomorrow=False):
    """Создать карточку, если её ещё нет. due_tomorrow — «попадает в повторение на завтра»."""
    lookup = {"child": child}
    if skill is not None:
        lookup.update(item_type="skill", skill=skill)
    elif word is not None:
        lookup.update(item_type="word", word=word)
    else:
        lookup.update(item_type="exercise", exercise=exercise)
    p = params()
    st = new_card(today, p)
    item, created = ReviewItem.objects.get_or_create(
        **lookup, defaults={"n": st.n, "ease_factor": st.ef, "interval_days": st.interval, "due_date": st.due}
    )
    if not created and due_tomorrow:
        tomorrow = today + dt.timedelta(days=1)
        if item.due_date > tomorrow:
            item.due_date = tomorrow
            item.save(update_fields=["due_date"])
    return item


@transaction.atomic
def record_review(item: ReviewItem, q: int, today: dt.date, rng=None):
    """SR-4: формула обновляется только по ПЕРВОМУ ответу дня. Возвращает True, если обновили."""
    item = ReviewItem.objects.select_for_update().get(pk=item.pk)
    if item.last_reviewed == today:
        return False
    before = item.state()
    after = schedule(before, q, today, rng or default_rng(), params())
    item.n, item.ease_factor, item.interval_days = after.n, after.ef, after.interval
    item.due_date, item.last_reviewed, item.lapses = after.due, after.last_reviewed, after.lapses
    item.reviews_count += 1
    item.fail_streak = item.fail_streak + 1 if q < 3 else 0
    item.save()
    ReviewLog.objects.create(review_item=item, q=q, ef_before=before.ef, ef_after=after.ef,
                             interval_before=before.interval, interval_after=after.interval)
    return True


def due_items(child, today):
    """SR-2: просроченность (desc) → EF (asc)."""
    return (ReviewItem.objects.filter(child=child, due_date__lte=today)
            .select_related("skill__topic__unit__subject", "word", "exercise__skill")
            .order_by("due_date", "ease_factor", "id"))
