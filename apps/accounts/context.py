from .utils import get_child


def child_context(request):
    child = get_child(request) if hasattr(request, "user") else None
    if not child:
        return {}
    from apps.rewards.stars import balance
    from apps.rewards.models import Streak

    streak = Streak.objects.filter(child=child).first()
    return {
        "current_child": child,
        "star_balance": balance(child),
        "streak_current": streak.current if streak else 0,
    }
