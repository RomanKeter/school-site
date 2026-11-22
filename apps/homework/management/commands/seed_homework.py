"""Загрузить формулировки для поиска «Моя домашка» из content_samples/homework_aliases.json (идемпотентно)."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.content.models import Skill, Topic
from apps.homework.models import SearchAlias

DEFAULT = Path(__file__).resolve().parents[4] / "content_samples" / "homework_aliases.json"


class Command(BaseCommand):
    help = "seed_homework [путь] — формулировки тем для «Моя домашка»"

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(DEFAULT))

    def handle(self, path, **kw):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        n = missing = 0
        for key, phrases in data.get("skills", {}).items():
            obj = Skill.objects.filter(external_key=key).first()
            if not obj:
                missing += 1
                continue
            SearchAlias.objects.update_or_create(skill=obj, defaults={"phrases": phrases})
            n += 1
        for key, phrases in data.get("topics", {}).items():
            obj = Topic.objects.filter(external_key=key).first()
            if not obj:
                missing += 1
                continue
            SearchAlias.objects.update_or_create(topic=obj, defaults={"phrases": phrases})
            n += 1
        self.stdout.write(self.style.SUCCESS(f"«Моя домашка»: формулировок {n}, не найдено {missing}"))
