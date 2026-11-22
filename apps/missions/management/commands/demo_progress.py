"""Демо-прогресс для показа кабинета родителя и карты островов: demo_progress [--child alesya]."""
import datetime as dt
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import ChildProfile
from apps.content.models import Exercise, Skill, VocabularyWord
from apps.learning.models import DiagnosticResult
from apps.learning.services import submit_answer
from apps.missions.models import DailyMission
from apps.rewards import streaks
from apps.srs.services import ensure_item


class Command(BaseCommand):
    help = "Сгенерировать правдоподобную историю занятий за 10 дней (только для демо!)"

    def add_arguments(self, parser):
        parser.add_argument("--child", default="alesya")

    def handle(self, child, **kw):
        rnd = random.Random(42)
        c = ChildProfile.objects.get(user__username=child)
        DiagnosticResult.objects.update_or_create(child=c, defaults={"completed_at": timezone.now()})
        today = timezone.localdate()
        plan = {  # навык → вероятность верного ответа
            "math.div.signs_2_5_10": 0.95, "math.div.signs_3_9": 0.85, "math.primes.notion": 0.8,
            "math.fr.notion": 0.9, "math.fr.compare": 0.2,
        }
        for back in range(10, 0, -1):
            day = today - dt.timedelta(days=back)
            for key, p in plan.items():
                sk = Skill.objects.get(external_key=key)
                for ex in Exercise.objects.filter(skill=sk).order_by("?")[:2]:
                    ok = rnd.random() < p
                    given = {"id": "__demo_ok__"} if ok else {"value": "__wrong__"}
                    # имитация: верно — через правильный ответ из answer
                    if ok:
                        a = ex.answer
                        given = ({"id": a["correct"][0]} if "correct" in a else
                                 {"buckets": a["buckets"]} if "buckets" in a else
                                 {"order": a["order"]} if "order" in a else
                                 {"pairs": a["pairs"]} if "pairs" in a else
                                 {"steps": [str(s["answer"]) for s in a["steps"]]} if "steps" in a else
                                 {"value": a.get("value")})
                    submit_answer(c, exercise=ex, given=given, attempt_no=1 if ok else 3, hints_used=0,
                                  duration_ms=15000, context="free", today=day)
            if back not in (4, 7):
                m, _ = DailyMission.objects.get_or_create(child=c, date=day)
                m.status = "done"
                m.save()
                streaks.on_mission_done(c, day)
        for w in VocabularyWord.objects.order_by("order")[:12]:
            ensure_item(c, today=today - dt.timedelta(days=1), word=w)
        self.stdout.write(self.style.SUCCESS("Демо-прогресс создан"))
