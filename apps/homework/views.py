from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.utils import child_required, local_today, parent_required
from apps.learning.views import _gate

from . import services
from .models import ContentRequest, HomeworkRequest


@child_required
def homework(request):
    """Э9 «Моя домашка»: поле «Что задали?» + предмет → 1–3 темы → «Тренироваться»."""
    gated = _gate(request)
    if gated:
        return gated
    child = request.child
    ctx = {"subject": request.POST.get("subject", ""), "text": "", "req": None, "msg": "", "max_chars": services.MAX_CHARS}
    if request.method == "POST":
        req, msg = services.submit(child, request.POST.get("text", ""), request.POST.get("subject"))
        ctx.update(text=request.POST.get("text", "")[:services.MAX_CHARS], req=req, msg=msg)
        if req:
            ctx["results"] = [dict(m, steps=services.steps_for(m)) for m in req.matches]
    ctx["recent"] = HomeworkRequest.objects.filter(child=child).exclude(matches=[])[:3] if request.method != "POST" else []
    return render(request, "homework/homework.html", ctx)


@child_required
@require_POST
def start(request, req_id):
    child = request.child
    req = get_object_or_404(HomeworkRequest, pk=req_id, child=child)
    try:
        obj_id = int(request.POST.get("id", ""))
    except ValueError:
        return redirect("homework")
    block = services.start_practice(req, request.POST.get("kind", ""), obj_id, local_today(child.family))
    if block is None:
        return redirect("homework")
    return redirect("play_block", block_id=block.id)


@parent_required
def parent_homework(request):
    family = request.parent.family
    if request.method == "POST":
        cr = get_object_or_404(ContentRequest, pk=request.POST.get("done"), family=family)
        cr.status = "done"
        cr.save(update_fields=["status"])
        messages.success(request, "Заявка отмечена как сделанная.")
        return redirect("parent_homework")
    return render(request, "homework/parent_homework.html", {
        "requests": HomeworkRequest.objects.filter(child__family=family).select_related("child", "chosen_skill", "chosen_topic")[:100],
        "content_requests": ContentRequest.objects.filter(family=family).select_related("child")[:100],
    })
