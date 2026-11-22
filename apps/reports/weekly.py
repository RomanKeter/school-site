"""Сбор данных недели, совет за ужином, карточка и отправка (разделы 13.2 и 23.6 ТЗ)."""
from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.utils import local_today
from apps.ai.models import AIQuery
from apps.content.models import Skill
from apps.learning.models import Attempt, SkillMastery
from apps.missions.models import DailyMission
from apps.rewards.models import StarTransaction
from apps.rewards.stars import balance as star_balance

from .models import DinnerTip, NotificationLog, WeeklyReport
from .render import html_for_card, render_png
from .senders import FakeSender, SendError, get_sender

log = logging.getLogger(__name__)

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

# Запасные советы, если у навыка и в банке пусто (D-605).
FALLBACK_TIPS = {
    "math": "Спросите: как поделить пиццу на 8 человек поровну, если её уже разрезали на 4 части?",
    "en": "Попросите научить вас 3 английским словам про еду, которые она выучила.",
    "ru": "Вспомните вместе: какое правило на этой неделе было самым интересным, и придумайте к нему свой пример.",
    "": "Спросите, что на этой неделе получилось легче всего, и порадуйтесь вместе.",
}

FORBIDDEN_WORDS = ("слабая", "слабый", "слабые", "ошибка", "ошибке", "ошибки", "ошибку")


def week_bounds(day: dt.date) -> tuple[dt.date, dt.date]:
    start = day - dt.timedelta(days=day.weekday())  # понедельник
    return start, start + dt.timedelta(days=6)


def rus_range(start: dt.date, end: dt.date) -> str:
    if start.month == end.month:
        return f"{start.day}–{end.day} {MONTHS[end.month - 1]}"
    return f"{start.day} {MONTHS[start.month - 1]} – {end.day} {MONTHS[end.month - 1]}"


def week_stats(child, week_start: dt.date) -> dict:
    week_end = week_start + dt.timedelta(days=6)
    days = []
    for i in range(7):
        d = week_start + dt.timedelta(days=i)
        done = DailyMission.objects.filter(child=child, date=d, status="done").exists()
        days.append({"date": d.isoformat(), "label": WEEKDAYS[i], "done": done})
    missions = DailyMission.objects.filter(child=child, date__gte=week_start, date__lte=week_end)
    minutes = int((missions.aggregate(s=Sum("active_seconds"))["s"] or 0) // 60)
    missions_done = missions.filter(status="done").count()
    stars_week = int(StarTransaction.objects.filter(child=child, day__gte=week_start, day__lte=week_end).aggregate(s=Sum("amount"))["s"] or 0)
    start_dt = timezone.make_aware(dt.datetime.combine(week_start, dt.time.min))
    end_dt = timezone.make_aware(dt.datetime.combine(week_end, dt.time.max))
    mastered = []
    qs = (SkillMastery.objects.filter(child=child, status="mastered", mastered_at__gte=start_dt, mastered_at__lte=end_dt)
          .select_related("skill", "skill__topic__unit__subject").order_by("mastered_at"))
    for m in qs[:3]:
        subj = m.skill.topic.unit.subject
        mastered.append({"title": m.skill.title, "skill_id": m.skill_id, "subject": subj.code, "subject_title": subj.title})
    practice = _practice_topic(child, week_start, week_end)
    ai_qs = AIQuery.objects.filter(child=child, created_at__gte=start_dt, created_at__lte=end_dt)
    ai_count = ai_qs.count()
    ai_refused = ai_qs.filter(refused=True).count()
    return {
        "child_name": child.display_name,
        "child_id": child.pk,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "week_label": rus_range(week_start, week_end),
        "days": days,
        "minutes": minutes,
        "missions_done": missions_done,
        "stars_week": stars_week,
        "stars_total": star_balance(child),
        "mastered": mastered,
        "practice": practice,
        "ai_count": ai_count,
        "ai_refused": ai_refused,
    }


def _practice_topic(child, week_start, week_end) -> dict | None:
    """Одна тема «потренироваться» без слов «слабая/ошибка» (IMP-REP-2). Критерий как у кабинета родителя."""
    start_dt = timezone.make_aware(dt.datetime.combine(week_start, dt.time.min))
    for m in SkillMastery.objects.filter(child=child).select_related("skill").order_by("mastery"):
        if m.attempts_count >= 6 and m.mastery < 0.6:
            return {"title": m.skill.title, "skill_id": m.skill_id}
    since = start_dt
    for m in SkillMastery.objects.filter(child=child).select_related("skill"):
        last3 = list(Attempt.objects.filter(child=child, exercise__skill=m.skill, is_final=True, created_at__gte=since).order_by("-created_at")[:3])
        if len(last3) == 3 and not any(a.is_correct for a in last3):
            return {"title": m.skill.title, "skill_id": m.skill_id}
    return None


def _tip_for_skill(skill) -> str | None:
    tip = (skill.dinner_tip or "").strip()
    if tip:
        return tip
    bank = DinnerTip.objects.filter(subject=skill.topic.unit.subject, is_active=True).order_by("id").first()
    if bank:
        return bank.text
    return None


def pick_dinner_tip(child, stats: dict) -> str:
    ids = [m["skill_id"] for m in stats.get("mastered") or [] if m.get("skill_id")]
    skills = list(Skill.objects.filter(pk__in=ids).select_related("topic__unit__subject"))
    by_id = {s.pk: s for s in skills}
    last_code = ""
    for item in stats.get("mastered") or []:
        skill = by_id.get(item.get("skill_id"))
        if not skill:
            continue
        tip = _tip_for_skill(skill)
        if tip:
            return tip
        last_code = skill.topic.unit.subject.code
    if last_code:
        return FALLBACK_TIPS.get(last_code, FALLBACK_TIPS[""])
    if stats.get("practice"):
        skill = Skill.objects.filter(pk=stats["practice"]["skill_id"]).select_related("topic__unit__subject").first()
        if skill:
            tip = _tip_for_skill(skill)
            if tip:
                return tip
            return FALLBACK_TIPS.get(skill.topic.unit.subject.code, FALLBACK_TIPS[""])
    bank = DinnerTip.objects.filter(is_active=True).select_related("subject").order_by("subject__order", "id").first()
    if bank:
        return bank.text
    return FALLBACK_TIPS[""]


def _file_uri(rel: str) -> str:
    return (Path(settings.BASE_DIR) / "static" / rel).resolve().as_uri()


def card_context(stats: dict, tip: str) -> dict:
    return {
        **stats,
        "tip": tip,
        "mascot": _file_uri("img/mascot/zubrik-party.svg"),
        "font_cyr_500": _file_uri("fonts/manrope-cyrillic-500-normal.woff2"),
        "font_lat_500": _file_uri("fonts/manrope-latin-500-normal.woff2"),
        "font_cyr_700": _file_uri("fonts/manrope-cyrillic-700-normal.woff2"),
        "font_lat_700": _file_uri("fonts/manrope-latin-700-normal.woff2"),
        "font_cyr_800": _file_uri("fonts/manrope-cyrillic-800-normal.woff2"),
        "font_lat_800": _file_uri("fonts/manrope-latin-800-normal.woff2"),
    }


def make_caption(stats: dict, tip: str) -> str:
    site = getattr(settings, "TELEGRAM_REPORT", {}).get("SITE_URL", "").rstrip("/")
    link = f"{site}/parent/" if site else "кабинет родителя на сайте"
    parts = [
        f"{stats['child_name']}, неделя {stats['week_label']}: миссий {stats['missions_done']} из 7, {stats['minutes']} мин, звёзд за неделю +{stats['stars_week']}.",
    ]
    if stats["mastered"]:
        titles = ", ".join(m["title"] for m in stats["mastered"])
        parts.append(f"Получилось: {titles}.")
    if stats["practice"]:
        parts.append(f"Потренироваться: {stats['practice']['title']}.")
    if stats["ai_count"]:
        parts.append(f"Вопросов к Масе: {stats['ai_count']} (из них отказов: {stats['ai_refused']}).")
    parts.append(f"Совет за ужином: {tip}")
    parts.append(f"Подробности — {link}")
    text = " ".join(parts)
    return text[:1024]  # лимит подписи Telegram


def make_text_report(stats: dict, tip: str) -> str:
    """Текстовая версия недельного отчёта (TG-3). Без слов «слабая/ошибка»."""
    lines = [
        f"Неделя {stats['week_label']}: {stats['child_name']}",
        f"Миссий: {stats['missions_done']} из 7, {stats['minutes']} мин, звёзд за неделю +{stats['stars_week']}.",
    ]
    days = " ".join(("✓" if d["done"] else "·") + d["label"] for d in stats["days"])
    lines.append(days)
    if stats["mastered"]:
        lines.append("Получилось: " + ", ".join(m["title"] for m in stats["mastered"]) + ".")
    if stats["practice"]:
        lines.append("Потренироваться: " + stats["practice"]["title"] + ".")
    if stats["ai_count"]:
        lines.append(f"Вопросов к Масе: {stats['ai_count']}, отказов: {stats['ai_refused']}.")
    lines.append("За ужином: " + tip)
    site = getattr(settings, "TELEGRAM_REPORT", {}).get("SITE_URL", "").rstrip("/")
    if site:
        lines.append(f"{site}/parent/")
    return "\n".join(lines)


def assert_kind_language(*texts: str) -> None:
    blob = " ".join(texts).lower()
    for w in FORBIDDEN_WORDS:
        if w in blob:
            raise ValueError(f"В отчёте нельзя слово «{w}»")


def _purge_old_images(keep_days=30):
    cutoff = timezone.now() - dt.timedelta(days=keep_days)
    for rep in WeeklyReport.objects.filter(sent_at__lt=cutoff).exclude(image=""):
        rep.image.delete(save=False)
        WeeklyReport.objects.filter(pk=rep.pk).update(image="")


def send_weekly_report(child, *, sender=None, week_start: dt.date | None = None, is_test=False, parent=None):
    """Собирает карточку, сохраняет WeeklyReport, отправляет, если есть chat_id и sender умеет слать."""
    if week_start is None:
        week_start, _ = week_bounds(local_today(child.family))
    if parent is None:
        parent = child.family.parents.first()
    stats = week_stats(child, week_start)
    tip = pick_dinner_tip(child, stats)
    caption = make_caption(stats, tip)
    text = make_text_report(stats, tip)
    assert_kind_language(caption, text, tip, *(m["title"] for m in stats["mastered"]),
                         stats["practice"]["title"] if stats.get("practice") else "")
    html = html_for_card(card_context(stats, tip))
    png = render_png(html)
    report, _ = WeeklyReport.objects.get_or_create(child=child, week_start=week_start)
    if report.image:
        report.image.delete(save=False)
    report.tip_text = tip
    report.caption = caption
    report.stats = stats
    report.is_test = is_test
    report.image.save(f"week_{child.pk}_{week_start.isoformat()}.png", ContentFile(png), save=False)

    log_kind = "test" if is_test else "weekly"
    nlog = NotificationLog.objects.create(parent=parent, kind=log_kind, payload={"child": child.pk, "week_start": week_start.isoformat()}, status="queued")
    report.notification = nlog

    fmt = getattr(parent, "weekly_report_format", "image") or "image"
    chat_id = (parent.telegram_chat_id or "").strip()
    sender = sender if sender is not None else get_sender()
    sent = False
    if chat_id:
        try:
            if fmt in ("text", "both"):
                sender.send_message(chat_id, text)
            if fmt in ("image", "both"):
                sender.send_photo(chat_id, png, caption)
            sent = True
            nlog.status = "sent"
            nlog.sent_at = timezone.now()
            nlog.error = ""
        except SendError as e:
            nlog.status = "error"
            nlog.error = str(e)[:240]
            log.warning("Не удалось отправить недельный отчёт")
    else:
        nlog.status = "error"
        nlog.error = "нет chat_id"
    nlog.save()
    report.sent_at = nlog.sent_at if sent else None
    report.save()
    _purge_old_images()
    return report
