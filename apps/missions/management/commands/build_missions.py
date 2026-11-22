"""Сборка миссий дня для всех детей (для systemd-таймера в 04:00 по Минску)."""
from django.core.management.base import BaseCommand

from apps.accounts.models import ChildProfile
from apps.accounts.utils import local_today
from apps.missions.builder import ensure_mission


class Command(BaseCommand):
    help = "Собрать миссию дня для всех детей (идемпотентно)"

    def handle(self, **kw):
        n = 0
        for child in ChildProfile.objects.select_related("family", "settings"):
            ensure_mission(child, local_today(child.family))
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Миссии готовы: {n}"))
