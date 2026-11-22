from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.utils import child_required, local_today, parent_required
from apps.content.models import Exercise, Skill
from apps.learning import player
from apps.learning.models import Block
from apps.learning.views import _gate

from . import feynman, helper, limits
from .models import AIQuery, AISettings, FeynmanSession
from .providers import get_provider


@child_required
@require_POST
def ask_masya(request, block_id, exercise_id):
    """HTMX: ответ Маси в #ai-panel на экране задания."""
    gated = _gate(request)
    if gated:
        return gated
    child = request.child
    block = get_object_or_404(Block, pk=block_id, child=child)
    ex = get_object_or_404(Exercise, pk=exercise_id)
    ctx = {"blk": block, "exercise": ex}
    if not limits.settings_for(child).enabled:
        ctx.update(r={"text": limits.MSG_OFF, "can_more": False})
        return render(request, "ai/_reply.html", ctx)
    if player.current_exercise_id(block) != ex.id:
        ctx.update(r={"text": "Это задание уже решено. Идём дальше!", "can_more": False})
        return render(request, "ai/_reply.html", ctx)
    prev = ""
    prev_id = request.POST.get("prev")
    if prev_id and prev_id.isdigit():
        prev = AIQuery.objects.filter(pk=int(prev_id), child=child, exercise=ex).values_list("answer", flat=True).first() or ""
    turn = request.POST.get("turn", "1")
    r = helper.ask(child, ex, request.POST.get("q", ""), turn=int(turn) if turn.isdigit() else 1,
                   prev_answer=prev, today=local_today(child.family))
    last = AIQuery.objects.filter(child=child, exercise=ex).order_by("-id").values_list("id", flat=True).first()
    ctx.update(r=r, next_turn=r["turn"] + 1, prev_id=last)
    return render(request, "ai/_reply.html", ctx)


@child_required
def teach_list(request):
    gated = _gate(request)
    if gated:
        return gated
    child = request.child
    if not limits.settings_for(child).teach_enabled:
        raise Http404
    return render(request, "ai/teach_list.html", {"topics": feynman.topics_for(child)})


@child_required
def teach(request, skill_id):
    gated = _gate(request)
    if gated:
        return gated
    child = request.child
    if not limits.settings_for(child).teach_enabled:
        raise Http404
    skill = get_object_or_404(Skill, pk=skill_id, feynman__enabled=True)
    if not feynman.is_open(child, skill):
        return redirect("ai_teach_list")
    session = feynman.current_session(child, skill)
    result = None
    if request.method == "POST":
        today = local_today(child.family)
        if request.POST.get("action") == "finish":
            result = {"reply": "Спасибо за урок! Я многое поняла.", "finished": True, "stars": feynman.finish(session, today)}
        else:
            result = feynman.submit(session, request.POST.get("text", ""), today)
        session.refresh_from_db()
    return render(request, "ai/teach.html", {
        "skill": skill, "topic": skill.feynman, "session": session, "result": result,
        "max_chars": feynman.MAX_CHARS,
    })


@parent_required
def parent_ai(request):
    parent = request.parent
    children = parent.family.children.all()
    child = get_object_or_404(children, pk=request.GET.get("child") or children.first().pk)
    s, _ = AISettings.objects.get_or_create(child=child)
    if request.method == "POST":
        s.enabled = request.POST.get("enabled") == "1"
        s.teach_enabled = request.POST.get("teach_enabled") == "1"
        try:
            s.daily_limit = max(0, min(30, int(request.POST.get("daily_limit", s.daily_limit))))
        except ValueError:
            pass
        s.save()
        messages.success(request, "Настройки ИИ сохранены.")
        return redirect(f"/parent/ai/?child={child.pk}")
    flt = request.GET.get("f", "all")
    qs = AIQuery.objects.filter(child=child).select_related("skill", "exercise")
    if flt == "refused":
        qs = qs.filter(refused=True)
    elif flt == "flagged":
        qs = qs.exclude(flags=[])
    return render(request, "ai/parent_ai.html", {
        "child": child, "children": children, "s": s, "queries": qs[:100], "f": flt,
        "sessions": FeynmanSession.objects.filter(child=child).select_related("skill")[:30],
        "used": limits.used_today(child, local_today(parent.family)),
        "month_cost": limits.month_cost(), "provider": get_provider().name,
    })
