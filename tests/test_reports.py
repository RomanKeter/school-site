"""Этап 2: недельный отчёт родителю в Telegram (разделы 13.2 и 23.6, D-600+). Сеть не используется."""
import datetime as dt
import io
import json
import struct
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.ai.models import AIQuery
from apps.content.models import Skill
from apps.learning.models import Attempt, SkillMastery
from apps.missions.models import DailyMission
from apps.reports.models import DinnerTip, NotificationLog, WeeklyReport
from apps.reports.senders import FakeSender, SendError, TelegramSender, TransientError, get_sender
from apps.reports.weekly import (
    FORBIDDEN_WORDS,
    make_caption,
    make_text_report,
    pick_dinner_tip,
    send_weekly_report,
    week_bounds,
    week_stats,
)
from apps.rewards.models import StarTransaction


def _png_size(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def _monday(day=None):
    day = day or dt.date(2026, 11, 22)  # воскресенье
    return week_bounds(day)[0]


@pytest.fixture
def week_child(family, content):
    """Родитель + ребёнок с понятной историей недели 16–22 ноября 2026."""
    parent, child = family
    parent.telegram_chat_id = "123456789"
    parent.weekly_report_format = "image"
    parent.save()
    week_start = dt.date(2026, 11, 16)
    skill = Skill.objects.get(external_key="math.fr.add")
    other = Skill.objects.get(external_key="math.fr.compare")
    Skill.objects.filter(pk=skill.pk).update(dinner_tip="Спросите: как поделить пиццу на 8 человек поровну, если её уже разрезали на 4 части?")
    skill.refresh_from_db()
    tz = timezone.get_current_timezone()
    mastered_at = timezone.make_aware(dt.datetime(2026, 11, 18, 12, 0), tz)
    SkillMastery.objects.create(child=child, skill=skill, mastery=0.9, status="mastered",
                                attempts_count=8, ever_mastered=True, mastered_at=mastered_at)
    SkillMastery.objects.create(child=child, skill=other, mastery=0.4, status="learning", attempts_count=8)
    for i, done in enumerate([True, True, False, True, True, False, True]):
        d = week_start + dt.timedelta(days=i)
        DailyMission.objects.create(child=child, date=d, status="done" if done else "pending",
                                    planned_seconds=15 * 60, active_seconds=(12 * 60 if done else 0))
    # 5 дней × 12 мин = 60 мин; 5 миссий
    for i, amt in enumerate([10, 8, 0, 12, 6, 0, 6]):
        if not amt:
            continue
        d = week_start + dt.timedelta(days=i)
        StarTransaction.objects.create(child=child, amount=amt, source_type="test", source_id=str(i), day=d)
    # 3 неверных финальных попытки на other — не обязательны при mastery<0.6 и 8 попытках
    ex = other.exercises.first()
    if ex:
        now = timezone.make_aware(dt.datetime(2026, 11, 20, 15, 0), tz)
        for n in range(3):
            Attempt.objects.create(child=child, exercise=ex, is_final=True, is_correct=False,
                                   attempt_no=n + 1, created_at=now)
    q1 = AIQuery.objects.create(child=child, kind="hint", question="как", answer="подсказка", refused=False)
    q2 = AIQuery.objects.create(child=child, kind="hint", question="дай ответ", answer="", refused=True)
    mid = timezone.make_aware(dt.datetime(2026, 11, 19, 10, 0), tz)
    AIQuery.objects.filter(pk__in=(q1.pk, q2.pk)).update(created_at=mid)
    return parent, child, week_start


def test_week_bounds_monday():
    start, end = week_bounds(dt.date(2026, 11, 22))
    assert start == dt.date(2026, 11, 16) and end == dt.date(2026, 11, 22)


def test_week_stats_numbers(week_child):
    parent, child, week_start = week_child
    s = week_stats(child, week_start)
    assert s["child_name"] == "Аня"
    assert s["missions_done"] == 5
    assert s["minutes"] == 60
    assert s["stars_week"] == 42
    assert s["days"][0]["done"] is True and s["days"][2]["done"] is False
    assert any(m["title"] == Skill.objects.get(external_key="math.fr.add").title for m in s["mastered"])
    assert s["practice"]["title"] == Skill.objects.get(external_key="math.fr.compare").title
    assert s["ai_count"] == 2 and s["ai_refused"] == 1
    blob = " ".join([make_caption(s, "совет"), make_text_report(s, "совет"), s["practice"]["title"]])
    for w in FORBIDDEN_WORDS:
        assert w not in blob.lower()


def test_dinner_tip_prefers_skill_then_bank(week_child):
    parent, child, week_start = week_child
    s = week_stats(child, week_start)
    tip = pick_dinner_tip(child, s)
    assert "пиццу" in tip
    Skill.objects.filter(external_key="math.fr.add").update(dinner_tip="")
    subj = Skill.objects.get(external_key="math.fr.add").topic.unit.subject
    DinnerTip.objects.create(subject=subj, text="Вспомните вместе: где дома можно найти прямой угол?", is_active=True)
    s = week_stats(child, week_start)
    tip = pick_dinner_tip(child, s)
    assert "прямой угол" in tip


def test_render_and_fake_send(week_child):
    parent, child, week_start = week_child
    sender = FakeSender()
    report = send_weekly_report(child, sender=sender, week_start=week_start, parent=parent)
    assert sender.sent and sender.sent[0]["type"] == "photo"
    photo = sender.sent[0]["photo"]
    assert _png_size(photo) == (1080, 1350)
    cap = sender.sent[0]["caption"]
    assert "Аня" in cap and "60" in cap and "+42" in cap
    assert "пиццу" in cap or "пиццу" in report.tip_text
    for w in FORBIDDEN_WORDS:
        assert w not in cap.lower() and w not in report.tip_text.lower()
    assert report.image and report.notification.status == "sent"
    assert WeeklyReport.objects.filter(child=child, week_start=week_start).count() == 1
    # повтор не плодит строки
    send_weekly_report(child, sender=FakeSender(), week_start=week_start, parent=parent)
    assert WeeklyReport.objects.filter(child=child, week_start=week_start).count() == 1


def test_format_text_and_both(week_child):
    parent, child, week_start = week_child
    parent.weekly_report_format = "text"
    parent.save()
    sender = FakeSender()
    send_weekly_report(child, sender=sender, week_start=week_start, parent=parent)
    assert [x["type"] for x in sender.sent] == ["message"]
    assert "Аня" in sender.sent[0]["text"] and "60" in sender.sent[0]["text"]
    parent.weekly_report_format = "both"
    parent.save()
    sender = FakeSender()
    send_weekly_report(child, sender=sender, week_start=week_start, parent=parent)
    assert [x["type"] for x in sender.sent] == ["message", "photo"]


def test_get_sender_ignores_other_bot_token(settings, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tarot-should-not-be-used")
    settings.TELEGRAM_REPORT = {**settings.TELEGRAM_REPORT, "BOT_TOKEN": ""}
    sender = get_sender()
    assert isinstance(sender, FakeSender)
    settings.TELEGRAM_REPORT = {**settings.TELEGRAM_REPORT, "BOT_TOKEN": "report-token-xyz"}
    sender = get_sender()
    assert isinstance(sender, TelegramSender)
    assert sender.token == "report-token-xyz"
    assert sender.token != "tarot-should-not-be-used"


class _Resp:
    def __init__(self, data=b'{"ok":true,"result":{}}'):
        self._data = data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass

    def read(self):
        return self._data


def test_telegram_sender_uses_report_token_and_retries(monkeypatch):
    urls, sleeps = [], []
    calls = {"n": 0}

    def fake_urlopen(req, timeout=20):
        urls.append(req.full_url)
        calls["n"] += 1
        if calls["n"] == 1:
            raise URLError("temporary")
        return _Resp()

    monkeypatch.setattr("apps.reports.senders.urlopen", fake_urlopen)
    sender = TelegramSender(token="REPORTTOKEN", delays=(1, 5, 15), sleeper=lambda s: sleeps.append(s), api_base="https://api.telegram.example")
    sender.send_photo("99", b"PNGDATA", "подпись")
    assert calls["n"] == 2 and sleeps == [1]
    assert all("REPORTTOKEN" in u for u in urls)
    assert all("tarot" not in u.lower() for u in urls)
    assert all(u.startswith("https://api.telegram.example/botREPORTTOKEN/") for u in urls)


def test_telegram_sender_no_retry_on_400(monkeypatch):
    def fake_urlopen(req, timeout=20):
        raise HTTPError(req.full_url, 400, "Bad Request", hdrs=None, fp=io.BytesIO(b'{"ok":false,"description":"chat not found"}'))

    monkeypatch.setattr("apps.reports.senders.urlopen", fake_urlopen)
    sender = TelegramSender(token="REPORTTOKEN", delays=(1, 5, 15), sleeper=lambda s: (_ for _ in ()).throw(AssertionError("не должны ждать")))
    with pytest.raises(SendError, match="chat not found"):
        sender.send_message("99", "привет")


def test_parent_settings_save_and_send_test(client, week_child):
    parent, child, week_start = week_child
    client.force_login(parent.user)
    r = client.get(f"/parent/settings/?child={child.pk}")
    assert r.status_code == 200 and "Отправить пробный отчёт" in r.content.decode() and "Chat id" in r.content.decode()
    r = client.post("/parent/telegram/", {
        "child": child.pk,
        "telegram_chat_id": "987654321",
        "weekly_report_format": "image",
        "save_telegram": "1",
    })
    assert r.status_code == 302
    parent.refresh_from_db()
    assert parent.telegram_chat_id == "987654321"
    r = client.post("/parent/telegram/", {
        "child": child.pk,
        "telegram_chat_id": "987654321",
        "weekly_report_format": "image",
        "send_test": "1",
    })
    assert r.status_code == 302 and "preview=" in r.url
    report = WeeklyReport.objects.get(child=child)
    r = client.get(r.url)
    assert r.status_code == 200 and f"/parent/weekly-image/{report.pk}/" in r.content.decode()
    img = client.get(f"/parent/weekly-image/{report.pk}/")
    assert img.status_code == 200 and img["Content-Type"] == "image/png"
    assert _png_size(b"".join(img.streaming_content)) == (1080, 1350)


def test_other_family_cannot_see_report_image(client, week_child):
    from apps.accounts.services import create_parent
    parent, child, week_start = week_child
    report = send_weekly_report(child, sender=FakeSender(), week_start=week_start, parent=parent)
    other = create_parent("parent2", "VeryLongPass456", family_name="Семья Б")
    client.force_login(other.user)
    assert client.get(f"/parent/weekly-image/{report.pk}/").status_code == 404
    assert client.post("/parent/telegram/", {"child": child.pk, "telegram_chat_id": "1", "send_test": "1"}).status_code == 404


def test_management_dry_run(week_child):
    parent, child, week_start = week_child
    call_command("send_weekly_reports", date="2026-11-22", dry_run=True)
    assert WeeklyReport.objects.filter(child=child, week_start=week_start).exists()
