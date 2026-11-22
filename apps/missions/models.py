from django.db import models


class DailyMission(models.Model):
    STATUSES = [("pending", "ждёт"), ("in_progress", "идёт"), ("done", "готово")]
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="missions")
    date = models.DateField()
    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    planned_seconds = models.PositiveIntegerField(default=15 * 60)
    active_seconds = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("child", "date")]
        verbose_name = "миссия дня"
        verbose_name_plural = "миссии"
