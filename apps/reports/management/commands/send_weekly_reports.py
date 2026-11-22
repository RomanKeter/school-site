"""Отправка недельных отчётов. Для cron: воскресенье 19:00 по таймзоне семьи (обычно Europe/Minsk)."""
import datetime as dt

from django.core.management.base import BaseCommand

from apps.accounts.models import ParentProfile
from apps.accounts.utils import local_today
from apps.reports.senders import FakeSender, get_sender
from apps.reports.weekly import send_weekly_report, week_bounds


class Command(BaseCommand):
    help = "Отправить недельные отчёты родителям с указанным chat id"

    def add_arguments(self, parser):
        parser.add_argument("--date", help="Якорь недели, YYYY-MM-DD (по умолчанию сегодня в TZ семьи)")
        parser.add_argument("--dry-run", action="store_true", help="Собрать карточки, никуда не отправлять")

    def handle(self, *args, **opts):
        sender = FakeSender() if opts["dry_run"] else get_sender()
        anchor = dt.date.fromisoformat(opts["date"]) if opts["date"] else None
        sent = skipped = errors = 0
        for parent in ParentProfile.objects.exclude(telegram_chat_id="").select_related("family"):
            week_start, _ = week_bounds(anchor or local_today(parent.family))
            for child in parent.family.children.all():
                report = send_weekly_report(child, sender=sender, week_start=week_start, parent=parent)
                if report.notification and report.notification.status == "sent":
                    sent += 1
                elif report.notification and report.notification.status == "error":
                    errors += 1
                else:
                    skipped += 1
        self.stdout.write(f"отправлено {sent}, ошибок {errors}, пропущено {skipped}")
