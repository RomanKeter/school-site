from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.utils import child_required, local_now, local_today
from apps.learning import services as learn_svc
from apps.learning.models import Block

from . import builder
from .models import DailyMission


@child_required
def home(request):
    child = request.child
    today = local_today(child.family)
    now = local_now(child.family)
    if learn_svc.is_quiet_hours(child, now):
        return render(request, "child/quiet.html", {"until": child.settings.quiet_to})
    if learn_svc.limit_reached(child, today):
        return render(request, "child/limit.html")
    act = learn_svc.activity_get(child, today)
    if act.break_started_at and (now - act.break_started_at).total_seconds() < 60:
        left = 60 - int((now - act.break_started_at).total_seconds())
        return render(request, "child/break.html", {"left": left})
    mission = builder.ensure_mission(child, today)
    blocks = list(mission.blocks.all())
    current = next((b for b in blocks if b.status != "done"), None)
    done_s = sum(b.est_seconds for b in blocks if b.status == "done")
    total_s = sum(b.est_seconds for b in blocks) or 1
    return render(request, "child/home.html", {
        "mission": mission,
        "blocks": blocks,
        "current": current,
        "progress_pct": int(100 * done_s / total_s),
        "left_min": max(0, (total_s - done_s) // 60),
    })


@child_required
@require_POST
def start_mission(request):
    child = request.child
    today = local_today(child.family)
    mission = builder.ensure_mission(child, today)
    if mission.status == "pending":
        mission.status = "in_progress"
        mission.save(update_fields=["status"])
    block = mission.blocks.exclude(status="done").order_by("order").first()
    if not block:
        return redirect("home")
    return redirect("play_block", block_id=block.id)


@child_required
def map_view(request, subject_code):
    from apps.content.models import Skill, Subject
    from apps.learning.models import SkillMastery
    from apps.learning.mastery import STATUS_VIEW, is_unlocked

    child = request.child
    subject = Subject.objects.filter(code=subject_code).first()
    skills = list(
        Skill.objects.filter(topic__unit__subject__code=subject_code, status="published")
        .select_related("topic").prefetch_related("prerequisites").order_by("topic__order", "order")
    )
    masteries = {m.skill_id: m for m in SkillMastery.objects.filter(child=child, skill__in=skills)}
    islands = []
    for sk in skills:
        m = masteries.get(sk.id)
        st = m.status if m else "not_started"
        pr = list(sk.prerequisites.all())
        pr_st = [(masteries[p.id].status if p.id in masteries else "not_started") for p in pr]
        locked = not is_unlocked(pr_st) if pr else False
        icon, label = STATUS_VIEW.get(st, ("🏝️", ""))
        islands.append({
            "skill": sk, "status": st, "icon": "🔒" if locked else icon,
            "label": "Сначала пройди: " + ", ".join(p.title for p in pr) if locked else label,
            "locked": locked,
        })
    return render(request, "child/map.html", {"subject": subject, "islands": islands})
