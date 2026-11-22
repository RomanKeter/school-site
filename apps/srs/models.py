from django.db import models


class SrsConfig(models.Model):
    """SR-7: параметры можно менять без изменения кода (одна активная запись)."""

    initial_ef = models.FloatField(default=2.5)
    min_ef = models.FloatField(default=1.3)
    max_ef = models.FloatField(default=2.8)
    i_max = models.PositiveSmallIntegerField(default=60)
    steps = models.JSONField(default=list)
    fuzz_pct = models.FloatField(default=0.10)
    daily_limit_default = models.PositiveSmallIntegerField(default=15)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "настройки повторения"
        verbose_name_plural = "настройки повторения"

    def to_params(self):
        from .algorithm import SrsParams

        return SrsParams(self.initial_ef, self.min_ef, self.max_ef, self.i_max,
                         tuple(self.steps or (1, 3, 7)), self.fuzz_pct)


class ReviewItem(models.Model):
    ITEM_TYPES = [("skill", "навык"), ("word", "слово"), ("exercise", "задание")]
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="review_items")
    item_type = models.CharField(max_length=10, choices=ITEM_TYPES)
    skill = models.ForeignKey("content.Skill", null=True, blank=True, on_delete=models.CASCADE)
    word = models.ForeignKey("content.VocabularyWord", null=True, blank=True, on_delete=models.CASCADE)
    exercise = models.ForeignKey("content.Exercise", null=True, blank=True, on_delete=models.CASCADE)
    n = models.PositiveIntegerField(default=0)
    ease_factor = models.FloatField(default=2.5)
    interval_days = models.PositiveIntegerField(default=1)
    due_date = models.DateField()
    last_reviewed = models.DateField(null=True, blank=True)
    lapses = models.PositiveIntegerField(default=0)
    reviews_count = models.PositiveIntegerField(default=0)
    fail_streak = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["child", "due_date"])]
        constraints = [
            models.CheckConstraint(
                name="review_item_exactly_one_ref",
                condition=(
                    models.Q(item_type="skill", skill__isnull=False, word__isnull=True, exercise__isnull=True)
                    | models.Q(item_type="word", word__isnull=False, skill__isnull=True, exercise__isnull=True)
                    | models.Q(item_type="exercise", exercise__isnull=False, skill__isnull=True, word__isnull=True)
                ),
            ),
            models.UniqueConstraint(fields=["child", "skill"], condition=models.Q(skill__isnull=False), name="uniq_review_skill"),
            models.UniqueConstraint(fields=["child", "word"], condition=models.Q(word__isnull=False), name="uniq_review_word"),
        ]
        verbose_name = "карточка повторения"
        verbose_name_plural = "карточки повторения"

    def state(self):
        from .algorithm import CardState

        return CardState(self.n, self.ease_factor, self.interval_days, self.due_date, self.last_reviewed, self.lapses)

    def subject_code(self):
        if self.word_id:
            return "en"
        return self.skill.topic.unit.subject.code if self.skill_id else self.exercise.skill.topic.unit.subject.code

    def group_key(self):
        if self.word_id:
            return f"word-topic-{self.word.topic_id}"
        return f"skill-{self.skill_id or self.exercise.skill_id}"


class ReviewLog(models.Model):
    review_item = models.ForeignKey(ReviewItem, on_delete=models.CASCADE, related_name="logs")
    reviewed_at = models.DateTimeField(auto_now_add=True)
    q = models.PositiveSmallIntegerField()
    ef_before = models.FloatField()
    ef_after = models.FloatField()
    interval_before = models.PositiveIntegerField()
    interval_after = models.PositiveIntegerField()
