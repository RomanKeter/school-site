import datetime as dt

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.forms import ChildCreateForm
from apps.accounts.services import create_child
from apps.accounts.utils import local_today, parent_required, set_trusted_device
from apps.content.models import Skill, Subject
from apps.learning.models import AssignedSkill, Attempt, SkillMastery
from apps.missions.models import DailyMission
from apps.rewards.models import StarTransaction
from apps.rewards.stars import balance
from apps.srs.models import ReviewItem


@parent_required
def dashboard(request):
    parent = request.parent
    children = list(parent.family.children.all())
    child_id = request.GET.get("child")
    child = None
    if child_id:
        child = get_object_or_404(parent.family.children, pk=child_id)
    elif children:
        child = children[0]
    ctx = {"children": children, "child": child}
    if child:
        today = local_today(parent.family)
        mission = DailyMission.objects.filter(child=child, date=today).first()
        week = [today - dt.timedelta(days=i) for i in range(6, -1, -1)]
        done_days = set(
            DailyMission.objects.filter(child=child, date__in=week, status="done").values_list("date", flat=True)
        )
        # прогресс по предметам
        subjects = []
        for subj in Subject.objects.filter(code__in=("math", "en", "ru", "by")):
            if subj.code == "en":
                total = ReviewItem.objects.filter(child=child, item_type="word").count()
                learned = ReviewItem.objects.filter(child=child, item_type="word", interval_days__gte=7).count()
                subjects.append({"subject": subj, "label": f"{total} слов, выучено {learned}"})
            else:
                skills = Skill.objects.filter(topic__unit__subject=subj, status="published")
                total = skills.count() or 1
                mastered = SkillMastery.objects.filter(child=child, skill__in=skills, status="mastered").count()
                subjects.append({"subject": subj, "label": f"{int(100 * mastered / total)} % освоено", "pct": int(100 * mastered / total)})
        weak = []
        for m in SkillMastery.objects.filter(child=child).select_related("skill").order_by("mastery"):
            if m.attempts_count >= 6 and m.mastery < 0.6:
                last = (
                    Attempt.objects.filter(child=child, exercise__skill=m.skill, is_final=True, is_correct=False)
                    .select_related("exercise").order_by("-created_at").first()
                )
                weak.append({"mastery": m, "last": last})
            if len(weak) >= 5:
                break
        # 3+ ошибки подряд за последние 7 дней (FR-PAR-2)
        since = timezone.now() - dt.timedelta(days=7)
        for m in SkillMastery.objects.filter(child=child).select_related("skill"):
            if any(w["mastery"].skill_id == m.skill_id for w in weak):
                continue
            last3 = list(Attempt.objects.filter(child=child, exercise__skill=m.skill, is_final=True, created_at__gte=since)
                         .select_related("exercise").order_by("-created_at")[:3])
            if len(last3) == 3 and not any(a.is_correct for a in last3):
                weak.append({"mastery": m, "last": last3[0], "note": "3 ошибки подряд"})
        # fail streak reviews
        for it in ReviewItem.objects.filter(child=child, fail_streak__gte=2, skill__isnull=False).select_related("skill")[:3]:
            if not any(w["mastery"].skill_id == it.skill_id for w in weak):
                m = SkillMastery.objects.filter(child=child, skill=it.skill).first()
                if m:
                    weak.append({"mastery": m, "last": None, "note": "2 провала повторения подряд"})
        ctx.update({
            "mission": mission,
            "week": week,
            "done_days": done_days,
            "subjects": subjects,
            "weak": weak,
            "stars": balance(child),
            "settings": child.settings,
        })
    return render(request, "parent/dashboard.html", ctx)


@parent_required
def settings_view(request):
    parent = request.parent
    child = get_object_or_404(parent.family.children, pk=request.GET.get("child") or parent.family.children.first().pk)
    s = child.settings
    if request.method == "POST":
        s.daily_limit_min = int(request.POST.get("daily_limit_min", s.daily_limit_min))
        s.break_every_min = int(request.POST.get("break_every_min", s.break_every_min))
        qf = request.POST.get("quiet_from", "20:30")
        qt = request.POST.get("quiet_to", "07:30")
        s.quiet_from = dt.time.fromisoformat(qf)
        s.quiet_to = dt.time.fromisoformat(qt)
        s.srs_daily_limit = int(request.POST.get("srs_daily_limit", s.srs_daily_limit))
        days = request.POST.getlist("days_off")
        s.days_off = [int(d) for d in days]
        if request.POST.get("extend15"):
            today = local_today(parent.family)
            s.extra_minutes_date = today
            s.extra_minutes = 15
        s.save()
        messages.success(request, "Настройки сохранены.")
        return redirect(f"/parent/settings/?child={child.pk}")
    days = list(enumerate(["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]))
    return render(request, "parent/settings.html", {"child": child, "settings": s, "days": days, "children": parent.family.children.all()})


@parent_required
@require_POST
def trust_device(request):
    response = redirect("parent_dashboard")
    set_trusted_device(response, request.parent.family)
    messages.success(request, "Это устройство теперь семейное. Ребёнок сможет входить по аватарке.")
    return response


@parent_required
def add_child(request):
    parent = request.parent
    form = ChildCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        cd = form.cleaned_data
        if parent.family.children.filter(user__username=cd["login"].lower()).exists():
            form.add_error("login", "Такой логин уже есть.")
        else:
            create_child(
                parent.family, cd["login"], cd["display_name"], cd["picture_password"],
                avatar_code=cd["avatar_code"], grade=cd["grade"],
            )
            messages.success(request, f"Профиль «{cd['display_name']}» создан.")
            return redirect("parent_dashboard")
    return render(request, "parent/add_child.html", {"form": form})


@parent_required
@require_POST
def assign_skill(request):
    parent = request.parent
    child = get_object_or_404(parent.family.children, pk=request.POST.get("child"))
    skill = get_object_or_404(Skill, pk=request.POST.get("skill"))
    day = dt.date.fromisoformat(request.POST.get("date") or (local_today(parent.family) + dt.timedelta(days=1)).isoformat())
    AssignedSkill.objects.create(child=child, skill=skill, date=day)
    messages.success(request, f"Тема «{skill.title}» добавлена в миссию на {day.isoformat()}.")
    return redirect(f"/parent/?child={child.pk}")
