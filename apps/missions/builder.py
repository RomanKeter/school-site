"""Сборщик миссии дня (FR-MIS-1) + диагностика + interleaving в блоке повторения."""
from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.utils import timezone

from apps.content.models import Exercise, Skill, Subject, VocabularyWord
from apps.learning.models import AssignedSkill, Block, DiagnosticResult, SkillMastery
from apps.learning import mastery as mastery_mod
from apps.srs import services as srs_svc
from apps.srs.interleave import interleave

from .models import DailyMission

TARGET = 15 * 60  # секунд


def _skills_for(child, subject_code: str):
    return list(
        Skill.objects.filter(topic__unit__subject__code=subject_code, status="published")
        .select_related("topic__unit__subject")
        .order_by("topic__unit__order", "topic__order", "order")
    )


def current_skill(child, subject_code: str):
    """Следующий незакрытый навык с учётом prerequisites и диагностики."""
    skills = _skills_for(child, subject_code)
    masteries = {m.skill_id: m for m in SkillMastery.objects.filter(child=child, skill__in=skills)}
    for sk in skills:
        m = masteries.get(sk.id)
        status = m.status if m else "not_started"
        if status in ("mastered",):
            continue
        # prerequisites
        prereqs = list(sk.prerequisites.all())
        ok = True
        for p in prereqs:
            pm = masteries.get(p.id)
            if not mastery_mod.is_unlocked([(pm.status if pm else "not_started")]):
                ok = False
                break
        if not ok:
            continue
        if m and mastery_mod.is_frustrated(m.last_window or [], m.lessons_done):
            # вернуть prerequisite
            if prereqs:
                return prereqs[0]
        return sk
    return skills[-1] if skills else None


def _lesson_queue(skill, level=1):
    """Структура урока 4.3 упрощённо: worked → guided×2 → solo×4."""
    exs = list(Exercise.objects.filter(skill=skill, status="published").order_by("difficulty", "id"))
    if not exs:
        return []
    by_diff = {}
    for e in exs:
        by_diff.setdefault(e.difficulty, []).append(e)
    q = [{"t": "worked", "skill": skill.id}]
    guided = (by_diff.get(1) or by_diff.get(2) or exs)[:2]
    for e in guided:
        q.append({"t": "ex", "id": e.id, "stage": "guided"})
    solo_pool = by_diff.get(level) or by_diff.get(min(by_diff)) or exs
    for e in solo_pool[:4]:
        q.append({"t": "adaptive", "skill": skill.id, "prefer": e.id, "stage": "solo"})
    return q


def _word_queue(child, today, n=5):
    """5 новых слов: flashcard → picture choice → tiles (упрощённый цикл FR-EN-2)."""
    due_en = srs_svc.due_items(child, today).filter(item_type="word").count()
    if due_en > 25:
        return []
    learned_ids = set(
        child.review_items.filter(item_type="word").values_list("word_id", flat=True)
    )
    words = list(
        VocabularyWord.objects.filter(language="en", status="published")
        .exclude(id__in=learned_ids)
        .order_by("order", "id")[:n]
    )
    q = []
    for w in words:
        q.append({"t": "word", "id": w.id, "mode": "flashcard"})
        q.append({"t": "word", "id": w.id, "mode": "picture_choice"})
        q.append({"t": "word", "id": w.id, "mode": "tiles"})
    return q, words


def _review_queue(child, today, limit, budget_s):
    items = list(srs_svc.due_items(child, today)[:limit])
    items = interleave(items, key=lambda it: it.group_key())
    q = []
    used = 0
    for it in items:
        est = 30
        if used + est > budget_s:
            break
        q.append({"t": "review", "item": it.id})
        used += est
    return q, used


@transaction.atomic
def ensure_mission(child, today: dt.date | None = None) -> DailyMission:
    today = today or timezone.localdate()
    mission, created = DailyMission.objects.get_or_create(child=child, date=today)
    if not created and mission.blocks.exists():
        return mission

    # Дни без миссии
    if today.weekday() in (child.settings.days_off or []):
        Block.objects.create(
            child=child, mission=mission, order=0, kind="surprise",
            title="Сегодня выходной 🎁", queue=[], status="done", est_seconds=0,
        )
        mission.status = "done"
        mission.completed_at = timezone.now()
        mission.save()
        return mission

    # Диагностика (принятое улучшение №1)
    diag = DiagnosticResult.objects.filter(child=child).first()
    order = 0
    if diag is None or not diag.completed_at:
        q = _build_diagnostic(child)
        Block.objects.create(
            child=child, mission=mission, order=order, kind="diagnostic",
            title="Давай познакомимся", subject_code="math", queue=q,
            est_seconds=20 * 60, meta={"level": 1},
        )
        order += 1
        mission.planned_seconds = 20 * 60
        mission.save()
        return mission

    # 1. Разминка
    warm_skill = None
    mastered = SkillMastery.objects.filter(child=child, status="mastered").select_related("skill").first()
    if mastered:
        warm_skill = mastered.skill
    else:
        warm_skill = current_skill(child, "math")
    if warm_skill:
        ex = Exercise.objects.filter(skill=warm_skill, status="published", difficulty=1).order_by("?").first()
        queue = [{"t": "ex", "id": ex.id, "stage": "warmup"}] if ex else []
        Block.objects.create(
            child=child, mission=mission, order=order, kind="warmup", title="Разминка",
            subject_code=warm_skill.topic.unit.subject.code, skill=warm_skill, queue=queue, est_seconds=60,
            meta={"level": 1},
        )
        order += 1

    # 2. Повторение ≤ 40% ≈ 360 с, ≤ 15 карточек
    rev_q, rev_s = _review_queue(child, today, child.settings.srs_daily_limit, int(TARGET * 0.4))
    if rev_q:
        Block.objects.create(
            child=child, mission=mission, order=order, kind="review",
            title=f"Повторим {len(rev_q)}", queue=rev_q, est_seconds=rev_s or 180,
            meta={"level": 1},
        )
        order += 1

    # 3. Назначенный родителем навык
    assigned = AssignedSkill.objects.filter(child=child, date=today, used=False).select_related("skill").first()
    lesson_skill = assigned.skill if assigned else None
    # приоритет предметов по дню недели: Пн/Ср/Пт — math, Вт/Чт — en (русского в MVP нет)
    if lesson_skill is None:
        primary = "math" if today.weekday() in (0, 2, 4) else "en"
        # для en урок слов отдельно; skill-урок — math всегда если есть
        lesson_skill = current_skill(child, "math")
    if lesson_skill:
        Block.objects.create(
            child=child, mission=mission, order=order, kind="lesson",
            title=lesson_skill.title, subject_code="math", skill=lesson_skill,
            queue=_lesson_queue(lesson_skill), est_seconds=8 * 60, meta={"level": 1},
        )
        order += 1
        if assigned:
            assigned.used = True
            assigned.save(update_fields=["used"])

    # 4. Английские слова
    wq, words = _word_queue(child, today, 5)
    if wq:
        Block.objects.create(
            child=child, mission=mission, order=order, kind="words",
            title="5 слов (EN)", subject_code="en", queue=wq,
            est_seconds=5 * 60, meta={"level": 1, "word_ids": [w.id for w in words]},
        )
        order += 1

    # 5. Сюрприз
    Block.objects.create(
        child=child, mission=mission, order=order, kind="surprise",
        title="Сюрприз 🎁", queue=[{"t": "celebrate"}], est_seconds=30, meta={},
    )
    mission.status = "pending"
    mission.planned_seconds = TARGET
    mission.save()
    return mission


def _build_diagnostic(child):
    """~20 мин: по 2–3 задания с первых навыков math + несколько слов EN."""
    q = []
    for code in ("math",):
        skills = _skills_for(child, code)[:4]
        for sk in skills:
            for e in Exercise.objects.filter(skill=sk, status="published", difficulty=1).order_by("id")[:2]:
                q.append({"t": "ex", "id": e.id, "stage": "diag", "skill": sk.id})
    words = VocabularyWord.objects.filter(language="en", status="published").order_by("order")[:5]
    for w in words:
        q.append({"t": "word", "id": w.id, "mode": "picture_choice"})
    return q


def advance_block(block: Block):
    block.position += 1
    if block.position >= len(block.queue):
        block.status = "done"
        block.completed_at = timezone.now()
        if block.kind == "lesson" and block.skill_id:
            m, _ = SkillMastery.objects.get_or_create(child=block.child, skill=block.skill)
            m.lessons_done += 1
            m.save(update_fields=["lessons_done"])
            from apps.rewards import stars as stars_svc

            stars_svc.award(block.child, 5, "lesson", block.pk, today=timezone.localdate())
    else:
        block.status = "in_progress"
    block.save()


@transaction.atomic
def complete_mission_if_done(mission: DailyMission, today: dt.date):
    if mission.status == "done":
        return []
    blocks = list(mission.blocks.all())
    if not blocks or any(b.status != "done" for b in blocks if b.kind != "surprise"):
        # сюрприз закрываем когда всё остальное done
        others = [b for b in blocks if b.kind != "surprise"]
        if others and all(b.status == "done" for b in others):
            for b in blocks:
                if b.kind == "surprise" and b.status != "done":
                    b.status = "done"
                    b.completed_at = timezone.now()
                    b.save()
        else:
            return []
    if any(b.status != "done" for b in mission.blocks.all()):
        return []
    mission.status = "done"
    mission.completed_at = timezone.now()
    mission.save()
    from apps.rewards import streaks, badges
    from apps.rewards import stars as stars_svc

    stars_svc.award(mission.child, 10, "mission", f"{mission.pk}", today=today)
    st, comeback = streaks.on_mission_done(mission.child, today)
    return badges.evaluate(mission.child, "mission_done", comeback=comeback)
