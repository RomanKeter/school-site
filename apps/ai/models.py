"""ИИ-помощник Мася и «Научи Масю» (этап 2, раздел 9 и 23.3 ТЗ; D-100…D-108).

Модели вынесены в отдельное приложение, существующие модели не меняются.
"""
from django.db import models


class AISettings(models.Model):
    """Настройки ИИ для ребёнка. Меняет только родитель (страница «ИИ-помощник»)."""

    child = models.OneToOneField("accounts.ChildProfile", on_delete=models.CASCADE, related_name="ai_settings")
    enabled = models.BooleanField("кнопка «Спросить Масю» включена", default=False)  # D-109: включает родитель
    teach_enabled = models.BooleanField("«Научи Масю» включено", default=False)
    daily_limit = models.PositiveSmallIntegerField("вопросов в день", default=10)  # AI-1: 0–30

    class Meta:
        verbose_name = "настройки ИИ"
        verbose_name_plural = "настройки ИИ"


class AIQuery(models.Model):
    """Журнал для родителя (9.3 п. 7): вопрос после маскирования, ответ, провайдер, токены, флаги."""

    KINDS = [("hint", "Спросить Масю"), ("teach", "Научи Масю"), ("homework", "Моя домашка: подбор темы")]
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="ai_queries")
    kind = models.CharField(max_length=8, choices=KINDS, default="hint")
    skill = models.ForeignKey("content.Skill", null=True, blank=True, on_delete=models.SET_NULL)
    exercise = models.ForeignKey("content.Exercise", null=True, blank=True, on_delete=models.SET_NULL)
    question = models.TextField(blank=True)
    answer = models.TextField(blank=True)
    provider = models.CharField(max_length=20, blank=True)
    model = models.CharField(max_length=80, blank=True)
    tokens_in = models.PositiveIntegerField(default=0)
    tokens_out = models.PositiveIntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    units = models.FloatField(default=1)  # сколько «вопросов» из дневного лимита списано
    flags = models.JSONField(default=list, blank=True)  # pii, stopword, leak, retry, fallback, url, refused, error
    refused = models.BooleanField(default=False)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["child", "created_at"])]
        verbose_name = "запрос к ИИ"
        verbose_name_plural = "запросы к ИИ"


class FeynmanTopic(models.Model):
    """Эталон для «Научи Масю» (IMP-FEYN-3): 2–4 ключевые идеи навыка.

    key_points: [{"text": "...", "keywords": ["...", ...], "ask": "наивный вопрос Маси"}]
    """

    skill = models.OneToOneField("content.Skill", on_delete=models.CASCADE, related_name="feynman")
    enabled = models.BooleanField(default=True)
    opener = models.CharField("просьба Маси", max_length=300)
    starter = models.CharField("подсказка-опора", max_length=200, blank=True)
    key_points = models.JSONField(default=list)

    class Meta:
        verbose_name = "тема «Научи Масю»"
        verbose_name_plural = "темы «Научи Масю»"

    def __str__(self):
        return self.skill.title


class FeynmanSession(models.Model):
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="feynman_sessions")
    skill = models.ForeignKey("content.Skill", on_delete=models.CASCADE)
    input_mode = models.CharField(max_length=6, default="text")
    child_text = models.TextField(blank=True)  # все реплики ребёнка после маскирования
    rounds = models.PositiveSmallIntegerField(default=0)
    covered = models.JSONField(default=list)  # индексы ключевых идей
    ai_result = models.JSONField(default=dict, blank=True)  # последний разбор
    history = models.JSONField(default=list, blank=True)  # [{"who": "child"|"masya", "text": ...}]
    finished = models.BooleanField(default=False)
    stars_awarded = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "сессия «Научи Масю»"
        verbose_name_plural = "сессии «Научи Масю»"
