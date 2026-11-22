import pytest

from apps.accounts.services import create_child, create_parent


@pytest.fixture
def family(db):
    parent = create_parent("parent1", "VeryLongPass123", family_name="Семья А")
    child = create_child(parent.family, "kid1", "Аня", ["apple", "cat", "star", "ball"])
    child.settings.quiet_from = child.settings.quiet_to
    child.settings.save()
    return parent, child


@pytest.fixture
def content(db):
    from django.core.management import call_command
    from pathlib import Path

    from apps.rewards.badges import seed_badges

    seed_badges()
    base = Path(__file__).resolve().parent.parent / "content_samples"
    for n in ("math_divisibility.json", "math_fractions.json", "en_words.json", "en_program.json"):
        call_command("import_content", str(base / n), update=True)


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache

    cache.clear()
    yield
