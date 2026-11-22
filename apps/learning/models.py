from django.db import models


class Attempt(models.Model):
    """FR-LRN-8: каждая попытка записывается."""

    CONTEXTS = [("lesson", "урок"), ("review", "повторение"), ("mission", "миссия"),
                ("diagnostic", "диагностика"), ("free", "свободная практика"), ("words", "слова")]
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="attempts")
    exercise = models.ForeignKey("content.Exercise", null=True, blank=True, on_delete=models.PROTECT)
    word = models.ForeignKey("content.VocabularyWord", null=True, blank=True, on_delete=models.PROTECT)
    word_mode = models.CharField(max_length=20, blank=True)
    block = models.ForeignKey("learning.Block", null=True, blank=True, on_delete=models.SET_NULL)
    context = models.CharField(max_length=12, choices=CONTEXTS, default="mission")
    params = models.JSONField(default=dict, blank=True)
    answer_given = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(default=False)
    partial_score = models.FloatField(default=0)
    attempt_no = models.PositiveSmallIntegerField(default=1)
    hints_used = models.PositiveSmallIntegerField(default=0)
    solution_shown = models.BooleanField(default=False)
    is_final = models.BooleanField(default=False)
    duration_ms = models.PositiveIntegerField(default=0)
    q = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # офлайн-синхронизация (IMP-OFF-4, D-700+)
    client_uuid = models.UUIDField(null=True, blank=True, unique=True)
    client_created_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    offline = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["child", "created_at"]), models.Index(fields=["child", "exercise"])]


class SkillMastery(models.Model):
    STATUSES = [("not_started", "Не начат"), ("learning", "Учу"), ("almost", "Почти"),
                ("mastered", "Освоен"), ("refresh", "Нужно освежить")]
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="masteries")
    skill = models.ForeignKey("content.Skill", on_delete=models.CASCADE)
    mastery = models.FloatField(default=0)
    status = models.CharField(max_length=12, choices=STATUSES, default="not_started")
    attempts_count = models.PositiveIntegerField(default=0)
    last_window = models.JSONField(default=list)  # [[вес, "YYYY-MM-DD"], …] — последние 10
    distinct_days = models.PositiveSmallIntegerField(default=0)
    lessons_done = models.PositiveSmallIntegerField(default=0)
    placed = models.BooleanField(default=False)  # отмечен входной диагностикой как знакомый
    ever_mastered = models.BooleanField(default=False)
    mastered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("child", "skill")]


class Block(models.Model):
    """Блок миссии или отдельной практики: очередь «шагов» (заданий), позиция и состояние.

    queue — список задач: {"t":"ex","id":..} | {"t":"adaptive","skill":..,"stage":"guided|solo"}
      | {"t":"worked","skill":..} | {"t":"word","id":..,"mode":..} | {"t":"review","item":..}
    """

    KINDS = [("warmup", "Разминка"), ("review", "Повторим"), ("lesson", "Урок"), ("words", "5 слов"),
             ("surprise", "Сюрприз"), ("diagnostic", "Знакомство"), ("free", "Практика")]
    STATUSES = [("pending", "ждёт"), ("in_progress", "идёт"), ("done", "готово")]
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="blocks")
    mission = models.ForeignKey("missions.DailyMission", null=True, blank=True, on_delete=models.CASCADE, related_name="blocks")
    order = models.PositiveSmallIntegerField(default=0)
    kind = models.CharField(max_length=12, choices=KINDS)
    title = models.CharField(max_length=120)
    subject_code = models.CharField(max_length=10, blank=True)
    skill = models.ForeignKey("content.Skill", null=True, blank=True, on_delete=models.SET_NULL)
    queue = models.JSONField(default=list)
    position = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    meta = models.JSONField(default=dict, blank=True)
    est_seconds = models.PositiveIntegerField(default=180)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["mission", "order", "id"]


class AssignedSkill(models.Model):
    """FR-PAR-4 / FR-PAR-2: родитель ставит тему в миссию на дату."""

    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE)
    skill = models.ForeignKey("content.Skill", on_delete=models.CASCADE)
    date = models.DateField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class DiagnosticResult(models.Model):
    child = models.OneToOneField("accounts.ChildProfile", on_delete=models.CASCADE, related_name="diagnostic")
    completed_at = models.DateTimeField(null=True, blank=True)
    data = models.JSONField(default=dict)


class DailyActivity(models.Model):
    """Активное время за день — для лимита (GAM-12) и перерывов (GAM-13)."""

    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="activity")
    date = models.DateField()
    active_seconds = models.PositiveIntegerField(default=0)
    since_break_seconds = models.PositiveIntegerField(default=0)
    breaks_taken = models.PositiveSmallIntegerField(default=0)
    break_started_at = models.DateTimeField(null=True, blank=True)
    last_ping = models.DateTimeField(null=True, blank=True)
    reflection = models.CharField(max_length=10, blank=True)

    class Meta:
        unique_together = [("child", "date")]


class OfflinePackage(models.Model):
    """Пакет дня: миссия на сегодня и завтра (IMP-OFF-2)."""

    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="offline_packages")
    date = models.DateField()
    version = models.PositiveIntegerField(default=1)
    size_bytes = models.PositiveIntegerField(default=0)
    generated_at = models.DateTimeField(auto_now=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("child", "date")]
        verbose_name = "офлайн-пакет"
        verbose_name_plural = "офлайн-пакеты"


class SyncConflict(models.Model):
    """Расхождение офлайн-проверки и пересчёта на сервере (IMP-OFF-3)."""

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="sync_conflicts")
    client_result = models.JSONField(default=dict)
    server_result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "конфликт синхронизации"
        verbose_name_plural = "конфликты синхронизации"

