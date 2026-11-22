"""Загрузить ключевые идеи «Научи Масю» из content_samples/feynman_key_points.json (идемпотентно)."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.ai.models import FeynmanTopic
from apps.content.models import Skill

DEFAULT = Path(__file__).resolve().parents[4] / "content_samples" / "feynman_key_points.json"


class Command(BaseCommand):
    help = "seed_feynman [путь] — эталоны ключевых идей для «Научи Масю»"

    def add_arguments(self, parser):
        parser.add_argument("path", nargs="?", default=str(DEFAULT))

    def handle(self, path, **kw):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        n = missing = 0
        for key, item in data["skills"].items():
            skill = Skill.objects.filter(external_key=key).first()
            if not skill:
                missing += 1
                continue
            FeynmanTopic.objects.update_or_create(skill=skill, defaults={
                "opener": item["opener"], "starter": item.get("starter", ""), "key_points": item["key_points"],
            })
            n += 1
        self.stdout.write(self.style.SUCCESS(f"«Научи Масю»: тем {n}, не найдено навыков {missing}"))
