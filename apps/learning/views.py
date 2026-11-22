import json
import random

from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.utils import child_required, local_now, local_today
from apps.content.models import Exercise, VocabularyWord
from apps.missions import builder as mission_builder

from . import player, services
from .feedback import phrase
from .models import Block, DiagnosticResult


def _gate(request):
    child = request.child
    today = local_today(child.family)
    now = local_now(child.family)
    if services.is_quiet_hours(child, now):
        return render(request, "child/quiet.html", {"until": child.settings.quiet_to})
    if services.limit_reached(child, today):
        return render(request, "child/limit.html")
    act = services.activity_get(child, today)
    if act.break_started_at:
        elapsed = (now - act.break_started_at).total_seconds()
        if elapsed < 60:
            return render(request, "child/break.html", {"left": int(60 - elapsed)})
        act.break_started_at = None
        act.since_break_seconds = 0
        act.save(update_fields=["break_started_at", "since_break_seconds"])
    return None


@child_required
def play_block(request, block_id):
    gated = _gate(request)
    if gated:
        return gated
    child = request.child
    block = get_object_or_404(Block, pk=block_id, child=child)
    if block.status == "pending":
        block.status = "in_progress"
        block.save(update_fields=["status"])

    while True:
        ctx = player.resolve(block)
        if ctx["kind"] == "skip":
            mission_builder.advance_block(block)
            continue
        if ctx["kind"] == "done":
            return _finish_block(request, block)
        if ctx["kind"] == "celebrate":
            mission_builder.advance_block(block)
            awards = []
            if block.mission_id:
                awards = mission_builder.complete_mission_if_done(block.mission, local_today(child.family))
            return render(request, "child/celebrate.html", {"blk": block, "awards": awards, "reflect_options": REFLECT})
        if ctx["kind"] == "worked":
            return render(request, "child/worked.html", {"blk": block, "skill": ctx["skill"], "example": ctx["example"]})
        if ctx["kind"] == "exercise":
            ex = ctx["exercise"]
            if ex is None:
                mission_builder.advance_block(block)
                continue
            return render(request, "child/exercise.html", {
                "blk": block, "exercise": ex, "stage": ctx.get("stage"),
                "payload": ex.payload, "progress": f"{block.position + 1}/{len(block.queue)}",
                "hints_used": 0, "attempt_no": 1,
            })
        if ctx["kind"] == "word":
            word = ctx["word"]
            distractors = list(
                VocabularyWord.objects.filter(language="en", status="published", topic=word.topic)
                .exclude(pk=word.pk).order_by("?")[:3]
            )
            options = distractors + [word]
            random.shuffle(options)
            return render(request, "child/word.html", {
                "blk": block, "word": word, "mode": ctx["mode"], "options": options,
                "progress": f"{block.position + 1}/{len(block.queue)}",
            })
        break
    return redirect("home")


@child_required
@require_POST
def worked_next(request, block_id):
    block = get_object_or_404(Block, pk=block_id, child=request.child)
    mission_builder.advance_block(block)
    return redirect("play_block", block_id=block.id)


@child_required
@require_POST
def check_exercise(request, block_id, exercise_id):
    gated = _gate(request)
    if gated:
        return gated
    child = request.child
    block = get_object_or_404(Block, pk=block_id, child=child)
    ex = get_object_or_404(Exercise, pk=exercise_id)
    if player.current_exercise_id(block) != ex.id:
        # повторная отправка уже засчитанного задания — без повторного начисления (AC-1-08)
        return render(request, "partials/feedback.html", {
            "fb": {"correct": True, "phrase": "Уже засчитано 👍", "stars": 0, "is_final": True},
            "blk": block, "next_url": f"/play/{block.id}/",
        })
    try:
        given = json.loads(request.POST.get("answer", "{}"))
    except json.JSONDecodeError:
        return HttpResponseBadRequest("bad answer")
    attempt_no = int(request.POST.get("attempt_no", 1))
    hints_used = int(request.POST.get("hints_used", 0))
    duration_ms = int(request.POST.get("duration_ms", 0))
    show_solution = request.POST.get("show_solution") == "1"
    today = local_today(child.family)

    att, fb = services.submit_answer(
        child, exercise=ex, block=block, given=given, attempt_no=attempt_no,
        hints_used=hints_used, duration_ms=duration_ms,
        context=block.kind if block.kind != "lesson" else "lesson",
        solution_shown=show_solution, today=today, final_now=(block.kind == "diagnostic"),
    )
    if fb["is_final"]:
        _requeue_failed_review(block, fb)
        # диагностика: отметить placed при верном
        if block.kind == "diagnostic" and fb["correct"] and ex.skill_id:
            m = services.get_or_create_mastery(child, ex.skill)
            if not m.placed:
                m.placed = True
                if m.status == "not_started":
                    m.status = "almost"
                m.save()
        mission_builder.advance_block(block)
        _after_final(block, today)

    return render(request, "partials/feedback.html", {
        "fb": fb, "exercise": ex, "blk": block,
        "attempt_no": attempt_no, "hints_used": hints_used,
        "next_url": f"/play/{block.id}/" if fb["is_final"] else None,
    })


@child_required
@require_POST
def hint(request, block_id, exercise_id):
    child = request.child
    block = get_object_or_404(Block, pk=block_id, child=child)
    ex = get_object_or_404(Exercise, pk=exercise_id)
    level = int(request.POST.get("hints_used", 0)) + 1
    hints = (ex.payload or {}).get("hints") or []
    text = ""
    for h in hints:
        if int(h.get("level", 0)) == level:
            text = h.get("text", "")
            break
    if not text and hints:
        text = hints[min(level, len(hints)) - 1].get("text", "")
    return render(request, "partials/hint.html", {
        "text": text or "Подумай ещё раз — у тебя получится!",
        "level": level, "total": max(3, len(hints)),
        "phrase": phrase("hint"),
    })


@child_required
@require_POST
def check_word(request, block_id, word_id):
    child = request.child
    block = get_object_or_404(Block, pk=block_id, child=child)
    word = get_object_or_404(VocabularyWord, pk=word_id)
    step = player.current_step(block) or {}
    step_word = step.get("id") if step.get("t") == "word" else None
    if step.get("t") == "review":
        step_word = block.child.review_items.filter(pk=step.get("item")).values_list("word_id", flat=True).first()
    if step_word != word.id:
        return render(request, "partials/feedback.html", {
            "fb": {"correct": True, "phrase": "Уже засчитано 👍", "stars": 0, "is_final": True},
            "blk": block, "next_url": f"/play/{block.id}/",
        })
    mode = request.POST.get("mode", "flashcard")
    try:
        given = json.loads(request.POST.get("answer", "{}"))
    except json.JSONDecodeError:
        given = {"value": request.POST.get("answer", "")}
    attempt_no = int(request.POST.get("attempt_no", 1))
    duration_ms = int(request.POST.get("duration_ms", 0))
    today = local_today(child.family)

    if mode == "flashcard":
        # просто показ
        from apps.srs import services as srs_svc
        srs_svc.ensure_item(child, today=today, word=word)
        mission_builder.advance_block(block)
        return render(request, "partials/feedback.html", {
            "fb": {"correct": True, "phrase": "Запомнили!", "stars": 0, "is_final": True, "solution_steps": []},
            "blk": block, "next_url": f"/play/{block.id}/",
        })

    att, fb = services.submit_answer(
        child, word=word, word_mode=mode, block=block, given=given,
        attempt_no=attempt_no, hints_used=0, duration_ms=duration_ms,
        context="words" if block.kind == "words" else ("diagnostic" if block.kind == "diagnostic" else "review"), today=today,
        final_now=(block.kind == "diagnostic"),
    )
    if fb["is_final"]:
        _requeue_failed_review(block, fb)
        mission_builder.advance_block(block)
        _after_final(block, today)
        from apps.rewards import badges
        badges.evaluate(child, "word_learned")
    return render(request, "partials/feedback.html", {
        "fb": fb, "blk": block, "word": word,
        "next_url": f"/play/{block.id}/" if fb["is_final"] else None,
        "attempt_no": attempt_no,
    })


def _finish_block(request, block):
    child = request.child
    today = local_today(child.family)
    _after_final(block, today)
    awards = []
    if block.kind == "diagnostic":
        return render(request, "child/celebrate.html", {"blk": block, "awards": [], "reflect_options": REFLECT})
    if block.kind == "lesson" and block.skill_id:
        from .mastery import STATUS_VIEW
        from .models import SkillMastery
        m = SkillMastery.objects.filter(child=child, skill=block.skill).first()
        icon, label = STATUS_VIEW.get(m.status if m else "learning", ("🌱", "Учу"))
        if block.mission_id:
            mission_builder.complete_mission_if_done(block.mission, today)
        return render(request, "child/celebrate.html", {
            "blk": block, "awards": [], "reflect_options": REFLECT,
            "island": f"Остров «{block.skill.title}»: {icon} {label}",
        })
    if block.mission_id:
        awards = mission_builder.complete_mission_if_done(block.mission, today)
        nxt = block.mission.blocks.exclude(status="done").order_by("order").first()
        if nxt:
            return redirect("play_block", block_id=nxt.id)
    return render(request, "child/celebrate.html", {"blk": block, "awards": awards, "reflect_options": REFLECT})


@child_required
@require_POST
def activity_ping(request):
    child = request.child
    today = local_today(child.family)
    act = services.activity_get(child, today)
    now = timezone.now()
    # Считаем не чаще раза в 25 с (защита от накрутки/дублей вкладок)
    if act.last_ping and (now - act.last_ping).total_seconds() < 25:
        return JsonResponse({"ok": True})
    act.last_ping = now
    act.active_seconds += 30
    act.since_break_seconds += 30
    resp = {"ok": True}
    if act.since_break_seconds >= child.settings.break_every_min * 60:
        act.break_started_at = now
        act.breaks_taken += 1
        act.since_break_seconds = 0
        resp["redirect"] = "/home/"
    act.save()
    if services.limit_reached(child, today):
        resp["redirect"] = "/home/"
    return JsonResponse(resp)


REFLECT = [("easy", "😊", "было легко"), ("ok", "🙂", "нормально"), ("hard", "😮", "трудно")]


@child_required
@require_POST
def reflect(request):
    """Мини-рефлексия «Как тебе было?» (+1 ★ раз в день)."""
    child = request.child
    today = local_today(child.family)
    mood = request.POST.get("mood", "")
    if mood not in {c for c, _, _ in REFLECT}:
        return HttpResponseBadRequest("bad mood")
    act = services.activity_get(child, today)
    act.reflection = mood
    act.save(update_fields=["reflection"])
    from apps.rewards import stars as stars_svc
    got = stars_svc.award(child, 1, "reflection", today.isoformat(), today=today)
    msg = "Спасибо, что рассказала! Трудно — значит, мозг растёт 💪" if mood == "hard" else "Спасибо, что рассказала!"
    return HttpResponse(f'<p class="bubble" style="display:inline-block">{msg}{" ⭐ +1" if got else ""}</p>')


@child_required
def dictionary(request):
    child = request.child
    words = VocabularyWord.objects.filter(language="en", status="published").order_by("order")
    learned = set(child.review_items.filter(item_type="word").values_list("word_id", flat=True))
    return render(request, "child/dictionary.html", {"words": words, "learned": learned})


def _requeue_failed_review(block, fb):
    """SR-4: неверная карточка повторения показывается ещё раз в конце сессии (однократно)."""
    if block.kind != "review" or fb.get("correct"):
        return
    step = block.queue[block.position] if block.position < len(block.queue) else None
    if step and step.get("t") == "review" and not step.get("again"):
        block.queue = block.queue + [{**step, "again": True}]
        block.save(update_fields=["queue"])


def _after_final(block, today):
    if block.kind == "diagnostic" and block.status == "done":
        mission_builder.finish_diagnostic(block, today)
    elif block.mission_id and block.status == "done":
        mission_builder.complete_mission_if_done(block.mission, today)
