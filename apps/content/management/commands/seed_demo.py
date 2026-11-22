"""Создать демо-семью, бейджи и импортировать демо-контент."""
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.accounts.services import create_child, create_parent
from apps.content.models import Subject
from apps.rewards.badges import seed_badges


# Русский язык, 5 класс РБ: порядок юнитов — по учебной программе (D-206)
RU_FILES = ("ru_repeat.json", "ru_grammar.json", "ru_text.json", "ru_phonetics.json", "ru_orthography.json",
            "ru_orthography2.json", "ru_lexis.json", "ru_dictation.json")


class Command(BaseCommand):
    help = "seed_demo — родитель roman / ChildPass123!, ребёнок alesya (apple,cat,star,ball)"

    def handle(self, **kw):
        seed_badges()
        Subject.objects.get_or_create(code="math", defaults={"title": "Математика", "color_token": "math", "icon": "🔢", "order": 1})
        Subject.objects.get_or_create(code="en", defaults={"title": "Английский", "color_token": "en", "icon": "🔤", "order": 2})
        Subject.objects.get_or_create(code="ru", defaults={"title": "Русский язык", "color_token": "ru", "icon": "📝", "order": 3})
        samples = Path(__file__).resolve().parents[4] / "content_samples"
        for name in ("math_divisibility.json", "math_fractions.json", "en_words.json", *RU_FILES):
            call_command("import_content", str(samples / name), update=True)
        from apps.accounts.models import User
        if not User.objects.filter(username="roman").exists():
            parent = create_parent("roman", "ChildPass123!", email="roman@example.com", family_name="Семья Дацких")
        else:
            parent = User.objects.get(username="roman").parent_profile
        if not parent.family.children.filter(display_name="Алеся").exists():
            create_child(parent.family, "alesya", "Алеся", ["apple", "cat", "star", "ball"], avatar_code="fox", grade=5)
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "AdminPass123!", role="admin")
        self.stdout.write(self.style.SUCCESS(
            "Готово. Родитель: roman / ChildPass123!  Ребёнок: alesya, пароль 🍎🐱⭐⚽  Админ: admin / AdminPass123!"
        ))
