from .models import Badge, ChildBadge, Streak


DEFAULT_BADGES = [
    ("first_step", "Первый шаг", "Первая выполненная миссия", "👣", {"type": "mission_count", "value": 1}, 1),
    ("streak_3", "3 дня подряд", "Серия миссий 3 дня", "🔥", {"type": "streak", "value": 3}, 2),
    ("streak_7", "Неделя", "Серия миссий 7 дней", "🔥", {"type": "streak", "value": 7}, 3),
    ("streak_30", "Месяц", "Серия миссий 30 дней", "🏆", {"type": "streak", "value": 30}, 4),
    ("fraction_master", "Повелительница дробей", "Освоены навыки темы «Обыкновенные дроби»", "🍕", {"type": "topic_master", "topic_key": "math.fractions"}, 5),
    ("divisibility", "Знаток делимости", "Освоена тема «Делимость»", "➗", {"type": "topic_master", "topic_key": "math.divisibility"}, 6),
    ("words_50", "50 слов", "50 английских слов с интервалом ≥ 7", "📚", {"type": "words", "value": 50}, 7),
    ("persistent", "Упорство", "10 заданий, решённых верно после ошибки", "💪", {"type": "retry_ok", "value": 10}, 8),
    ("comeback", "С возвращением!", "Миссия после перерыва ≥ 3 дня", "👋", {"type": "comeback"}, 9),
]


def seed_badges():
    for code, title, desc, icon, rule, order in DEFAULT_BADGES:
        Badge.objects.update_or_create(
            code=code, defaults={"title": title, "description": desc, "icon": icon, "rule": rule, "order": order}
        )


def grant(child, code: str) -> ChildBadge | None:
    badge = Badge.objects.filter(code=code).first()
    if not badge:
        return None
    obj, created = ChildBadge.objects.get_or_create(child=child, badge=badge)
    return obj if created else None


def evaluate(child, event: str, **ctx):
    """Вызывается после событий. Возвращает список новых ChildBadge."""
    awarded = []
    if event == "mission_done":
        from apps.missions.models import DailyMission

        n = DailyMission.objects.filter(child=child, status="done").count()
        if n >= 1:
            b = grant(child, "first_step")
            if b:
                awarded.append(b)
        streak = Streak.objects.filter(child=child).first()
        if streak:
            for code, val in (("streak_3", 3), ("streak_7", 7), ("streak_30", 30)):
                if streak.current >= val:
                    b = grant(child, code)
                    if b:
                        awarded.append(b)
        if ctx.get("comeback"):
            b = grant(child, "comeback")
            if b:
                awarded.append(b)
    if event == "skill_mastered":
        skill = ctx.get("skill")
        if skill:
            topic = skill.topic
            skills = list(topic.skills.filter(status="published"))
            from apps.learning.models import SkillMastery

            mastered = SkillMastery.objects.filter(
                child=child, skill__in=skills, status="mastered"
            ).count()
            if skills and mastered >= len(skills):
                code = topic.badge_code
                if code:
                    b = grant(child, code)
                    if b:
                        awarded.append(b)
    if event == "retry_ok":
        from apps.learning.models import Attempt

        n = Attempt.objects.filter(child=child, is_correct=True, attempt_no__gte=2, is_final=True).count()
        if n >= 10:
            b = grant(child, "persistent")
            if b:
                awarded.append(b)
    if event == "word_learned":
        from apps.srs.models import ReviewItem

        n = ReviewItem.objects.filter(child=child, item_type="word", interval_days__gte=7).count()
        if n >= 50:
            b = grant(child, "words_50")
            if b:
                awarded.append(b)
    return awarded
