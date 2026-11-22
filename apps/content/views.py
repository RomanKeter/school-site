from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, render

from .models import Exercise


@staff_member_required
def preview_exercise(request, pk):
    """AC-1-11: предпросмотр задания из админки (как видит ребёнок + ответ и подсказки)."""
    ex = get_object_or_404(Exercise, pk=pk)
    return render(request, "content/preview.html", {"exercise": ex, "payload": ex.payload})
