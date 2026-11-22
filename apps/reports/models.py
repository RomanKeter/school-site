from django.db import models


class DinnerTip(models.Model):
    """Банк советов для разговора за ужином (IMP-REP-3), если у навыка пусто Skill.dinner_tip."""

    subject = models.ForeignKey("content.Subject", on_delete=models.CASCADE, related_name="dinner_tips")
    text = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "совет за ужином"
        verbose_name_plural = "советы за ужином"

    def __str__(self):
        return self.text[:60]


class NotificationLog(models.Model):
    KINDS = [
        ("daily", "ежедневный итог"),
        ("weekly", "недельный отчёт"),
        ("alert", "тревога"),
        ("ai_flag", "стоп-слово ИИ"),
        ("budget", "бюджет ИИ"),
        ("badge", "значок"),
        ("test", "пробная отправка"),
    ]
    STATUSES = [("queued", "в очереди"), ("sent", "отправлено"), ("error", "ошибка")]

    parent = models.ForeignKey("accounts.ParentProfile", on_delete=models.CASCADE, related_name="notification_logs")
    kind = models.CharField(max_length=12, choices=KINDS)
    payload = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUSES, default="queued")
    error = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "журнал уведомлений"
        verbose_name_plural = "журнал уведомлений"


class WeeklyReport(models.Model):
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="weekly_reports")
    week_start = models.DateField()
    image = models.FileField(upload_to="weekly_reports/", blank=True)
    tip_text = models.TextField(blank=True)
    caption = models.TextField(blank=True)
    stats = models.JSONField(default=dict, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    notification = models.ForeignKey(NotificationLog, null=True, blank=True, on_delete=models.SET_NULL)
    is_test = models.BooleanField(default=False)

    class Meta:
        unique_together = [("child", "week_start")]
        verbose_name = "недельный отчёт"
        verbose_name_plural = "недельные отчёты"

    def __str__(self):
        return f"{self.child} {self.week_start}"
