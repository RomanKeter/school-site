"""Сервисы обучения: попытки, mastery, адаптивность, выбор задания."""
from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.utils import timezone

from apps.srs import services as srs_svc
from apps.srs.algorithm import quality

from . import adaptive as adaptive_mod
from . import mastery as mastery_mod
from . import ru_types
from .checkers import check
from .feedback import phrase
from .models import Attempt, Block, DailyActivity, SkillMastery


def get_or_create_mastery(child, skill) -> SkillMastery:
    m, _ = SkillMastery.objects.get_or_create(child=child, skill=skill)
    return m


@transaction.atomic
def apply_mastery(child, skill, q: int, today: dt.date) -> SkillMastery:
    m = get_or_create_mastery(child, skill)
    day = today.isoformat()
    window = mastery_mod.push(m.last_window or [], q, day)
    m.last_window = window
    m.mastery = mastery_mod.mastery_value(window)
    m.attempts_count += 1
    m.distinct_days = mastery_mod.distinct_days(window)
    review = srs_svc.due_items(child, today).filter(skill=skill).first()
    fail_streak = review.fail_streak if review else 0
    new_status = mastery_mod.status(
        window, ever_mastered=m.ever_mastered, review_fail_streak=fail_streak, placed=m.placed
    )
    newly = new_status == "mastered" and not m.ever_mastered
    if newly:
        m.ever_mastered = True
        m.mastered_at = timezone.now()
    m.status = new_status
    m.save()
    if newly:
        from apps.rewards import badges
        from apps.rewards import stars as stars_svc

        stars_svc.award(child, 15, "skill_mastered", skill.pk, today=today)
        badges.evaluate(child, "skill_mastered", skill=skill)
    return m


def pick_exercise(skill, level: int, exclude_ids=None, for_warmup=False):
    from apps.content.models import Exercise

    qs = Exercise.objects.filter(skill=skill, status="published")
    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)
    if for_warmup:
        qs = qs.filter(difficulty=1)
    diffs = set(qs.values_list("difficulty", flat=True))
    d = adaptive_mod.pick_difficulty(diffs, level) if diffs else None
    if d is None:
        return None
    return qs.filter(difficulty=d).order_by("?").first()


@transaction.atomic
def submit_answer(child, *, exercise=None, word=None, word_mode="", block: Block | None = None,
                  given, attempt_no: int, hints_used: int, duration_ms: int, context: str,
                  solution_shown=False, today: dt.date | None = None, final_now=False,
                  client_uuid=None, client_created_at=None, offline=False):
    today = today or timezone.localdate()
    if client_uuid:
        found = Attempt.objects.filter(client_uuid=client_uuid).first()
        if found:
            return found, {
                "correct": found.is_correct, "partial": found.partial_score, "distractor": "",
                "is_final": found.is_final, "q": found.q, "phrase": "", "stars": 0,
                "solution_steps": [], "mastery_status": None, "duplicate": True,
            }
    if exercise:
        result = check(exercise.type, exercise.payload, exercise.answer, given)
        est = exercise.est_seconds
        skill = exercise.skill
    else:
        # проверка слова (режимы)
        result = _check_word(word, word_mode, given)
        est = 25
        skill = None

    q = quality(
        correct=result.correct,
        attempt_no=attempt_no,
        hints_used=hints_used,
        duration_s=duration_ms / 1000.0,
        est_seconds=est,
        skipped=solution_shown and not result.correct,
    )
    if solution_shown and not result.correct:
        q = 1

    is_final = result.correct or attempt_no >= 3 or solution_shown or final_now
    att = Attempt.objects.create(
        child=child, exercise=exercise, word=word, word_mode=word_mode, block=block,
        context=context, answer_given=given if isinstance(given, dict) else {"value": given},
        is_correct=result.correct, partial_score=result.partial, attempt_no=attempt_no,
        hints_used=hints_used, solution_shown=solution_shown, is_final=is_final,
        duration_ms=duration_ms, q=q if is_final else None,
        client_uuid=client_uuid, client_created_at=client_created_at,
        offline=offline, synced_at=timezone.now() if client_uuid else None,
    )

    feedback = {
        "correct": result.correct,
        "partial": result.partial,
        "distractor": result.distractor,
        "is_final": is_final,
        "q": q if is_final else None,
        "phrase": "",
        "stars": 0,
        "solution_steps": [],
        "mastery_status": None,
    }

    if result.correct:
        feedback["phrase"] = phrase("correct_first" if attempt_no == 1 and hints_used == 0 else "correct_retry")
        if exercise and exercise.type in ru_types.RU_TYPES:  # D-202: правило после верного ответа
            feedback["explain"] = (exercise.payload or {}).get("explain", "")
    elif is_final:
        feedback["phrase"] = phrase("solution")
        feedback["correct_answer"] = correct_answer_text(exercise=exercise, word=word, word_mode=word_mode)
        if exercise:
            feedback["solution_steps"] = (exercise.payload or {}).get("solution_steps") or []
            if exercise.type == "step_by_step":
                feedback["solution_steps"] = [
                    f"{s.get('ask', '')} → {s.get('answer')}" for s in (exercise.payload or {}).get("steps") or []
                ]
    else:
        feedback["phrase"] = result.distractor or phrase("almost")

    if is_final and skill is not None:
        m = apply_mastery(child, skill, q, today)
        feedback["mastery_status"] = m.status
        if context in ("lesson", "mission", "review", "diagnostic", "free"):
            srs_svc.ensure_item(child, today=today, skill=skill, due_tomorrow=not result.correct)
            if context == "review":
                item = child.review_items.filter(skill=skill).first()
                if item:
                    srs_svc.record_review(item, q, today)
        # адаптивность — в meta блока
        if block is not None:
            st = adaptive_mod.AdaptiveState(
                level=int(block.meta.get("level", 1)),
                right_streak=int(block.meta.get("right_streak", 0)),
                wrong_streak=int(block.meta.get("wrong_streak", 0)),
            )
            first_ok = result.correct and attempt_no == 1 and hints_used == 0
            st2 = adaptive_mod.update(st, first_ok)
            block.meta = {**block.meta, "level": st2.level, "right_streak": st2.right_streak, "wrong_streak": st2.wrong_streak}
            block.save(update_fields=["meta"])

    if is_final and word is not None:
        item = srs_svc.ensure_item(child, today=today, word=word, due_tomorrow=not result.correct)
        if context == "diagnostic" and result.correct and item.n == 0:
            # слово уже знакомо — сразу «успешное повторение»: следующий показ через 3 дня
            item.n, item.interval_days = 1, 3
            item.due_date = today + dt.timedelta(days=3)
            item.save(update_fields=["n", "interval_days", "due_date"])
        if context == "review":
            item = child.review_items.filter(word=word).first()
            if item:
                srs_svc.record_review(item, q, today)

    # звёзды
    from apps.rewards import stars as stars_svc

    if is_final:
        amount = 0
        if result.correct and attempt_no == 1 and hints_used == 0:
            amount = 2
        elif result.correct:
            amount = 1
        else:
            amount = 1  # «за упорство»: досмотрела разбор решения
        if amount:
            src = f"{block.pk}:{block.position}" if block is not None else f"a{att.pk}"
            feedback["stars"] = stars_svc.award(child, amount, "attempt", src, today=today)

    return att, feedback


def _check_word(word, mode, given):
    from .checkers import CheckResult, normalize_text

    raw = given.get("value") if isinstance(given, dict) else given
    if mode in ("ru_to_en", "tiles", "type"):
        ok = normalize_text(str(raw or "")) == normalize_text(word.word)
        return CheckResult(ok, 1.0 if ok else 0.0)
    if mode in ("en_to_ru", "choice_ru"):
        ok = normalize_text(str(raw or "")) == normalize_text(word.translation_ru)
        return CheckResult(ok, 1.0 if ok else 0.0)
    # picture/audio choice by id
    gid = given.get("id") if isinstance(given, dict) else given
    ok = str(gid) == str(word.pk)
    return CheckResult(ok, 1.0 if ok else 0.0)


def activity_get(child, today) -> DailyActivity:
    obj, _ = DailyActivity.objects.get_or_create(child=child, date=today)
    return obj


def is_quiet_hours(child, now) -> bool:
    s = child.settings
    t = now.time()
    if s.quiet_from <= s.quiet_to:
        return s.quiet_from <= t < s.quiet_to
    return t >= s.quiet_from or t < s.quiet_to


def limit_reached(child, today) -> bool:
    act = activity_get(child, today)
    return act.active_seconds >= child.settings.limit_for(today) * 60


def correct_answer_text(*, exercise=None, word=None, word_mode=""):
    """Правильный ответ для показа ПОСЛЕ исчерпания попыток (FR-LRN-3)."""
    if word is not None:
        if word_mode == "en_to_ru":
            return f"{word.word} — {word.translation_ru}"
        return f"{word.picture} {word.word} — {word.translation_ru}"
    if exercise is None:
        return ""
    if exercise.type in ru_types.RU_TYPES:  # D-202: слово/предложение целиком
        return ru_types.answer_text(exercise)
    a, p = exercise.answer or {}, exercise.payload or {}
    if "correct" in a:
        opts = {o["id"]: o["text"] for o in p.get("options", [])}
        return ", ".join(opts.get(c, c) for c in a["correct"])
    if "order" in a:
        items = {i["id"]: i["text"] for i in p.get("items", [])}
        return " → ".join(items.get(i, i) for i in a["order"])
    if "pairs" in a:
        left = {i["id"]: i["text"] for i in p.get("left", [])}
        right = {i["id"]: i["text"] for i in p.get("right", [])}
        return "; ".join(f"{left.get(k, k)} — {right.get(v, v)}" for k, v in a["pairs"].items())
    if "buckets" in a:
        titles = {b["id"]: b["title"] for b in p.get("buckets", [])}
        return "; ".join(f"{titles.get(b, b)}: {', '.join(v)}" for b, v in a["buckets"].items())
    if "steps" in a:
        return " → ".join(str(s.get("answer")) for s in a["steps"])
    if "value" in a:
        return ("x = " if exercise.type == "equation" else "") + str(a["value"])
    return ""
