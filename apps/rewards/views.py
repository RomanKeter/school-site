from django.shortcuts import render

from apps.accounts.utils import child_required

from .models import Badge, ChildBadge
from .stars import balance


@child_required
def rewards_home(request):
    child = request.child
    owned = {cb.badge_id: cb for cb in ChildBadge.objects.filter(child=child).select_related("badge")}
    upcoming = []
    for b in Badge.objects.filter(stage=1):
        if b.id not in owned:
            upcoming.append(b)
            if len(upcoming) >= 3:
                break
    return render(request, "child/rewards.html", {
        "balance": balance(child),
        "owned": list(owned.values()),
        "upcoming": upcoming,
        "streak": getattr(child, "streak", None),
    })
