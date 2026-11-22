from django.db import models


class StarTransaction(models.Model):
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="stars")
    amount = models.IntegerField()
    source_type = models.CharField(max_length=40)
    source_id = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)
    day = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["child", "source_type", "source_id"], name="uniq_star_source"),
        ]


class Badge(models.Model):
    code = models.CharField(max_length=40, unique=True)
    title = models.CharField(max_length=80)
    description = models.CharField(max_length=200)
    icon = models.CharField(max_length=8, default="🏅")
    rule = models.JSONField(default=dict)
    stage = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]


class ChildBadge(models.Model):
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    awarded_at = models.DateTimeField(auto_now_add=True)
    seen = models.BooleanField(default=False)

    class Meta:
        unique_together = [("child", "badge")]


class Streak(models.Model):
    child = models.OneToOneField("accounts.ChildProfile", on_delete=models.CASCADE, related_name="streak")
    current = models.PositiveIntegerField(default=0)
    best = models.PositiveIntegerField(default=0)
    last_counted_date = models.DateField(null=True, blank=True)
    freezes_available = models.PositiveSmallIntegerField(default=1)
    freezes_week = models.PositiveSmallIntegerField(default=0)  # номер недели ISO, когда начислили
