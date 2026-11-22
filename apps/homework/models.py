"""«Моя домашка» (раздел 5.8 ТЗ, D-300…). Отдельное приложение, существующие модели не меняются."""
from django.db import models


class SearchAlias(models.Model):
    """Дополнительные формулировки для поиска темы домашки (как пишет ребёнок или учительница).

    Ровно одно из skill / topic: навык (практика заданиями) или словарная тема английского (практика словами).
    """

    skill = models.OneToOneField("content.Skill", null=True, blank=True, on_delete=models.CASCADE, related_name="hw_alias")
    topic = models.OneToOneField("content.Topic", null=True, blank=True, on_delete=models.CASCADE, related_name="hw_alias")
    phrases = models.JSONField(default=list)

    class Meta:
        verbose_name = "формулировки для поиска домашки"
        verbose_name_plural = "формулировки для поиска домашки"


class HomeworkRequest(models.Model):
    METHODS = [("match", "поиск по темам"), ("ai", "ИИ-классификатор"), ("none", "не найдено")]
    child = models.ForeignKey("accounts.ChildProfile", on_delete=models.CASCADE, related_name="homework_requests")
    subject = models.ForeignKey("content.Subject", null=True, blank=True, on_delete=models.SET_NULL)
    text = models.CharField(max_length=200)  # после маскирования ПДн
    looks_like_task = models.BooleanField(default=False)  # FR-HW-5: ребёнок ввёл условие задачи
    match_method = models.CharField(max_length=6, choices=METHODS, default="none")
    matches = models.JSONField(default=list)  # [{"kind": "skill"|"words", "id": .., "title": .., "score": ..}]
    chosen_skill = models.ForeignKey("content.Skill", null=True, blank=True, on_delete=models.SET_NULL)
    chosen_topic = models.ForeignKey("content.Topic", null=True, blank=True, on_delete=models.SET_NULL)
    block = models.ForeignKey("learning.Block", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "запрос «Моя домашка»"
        verbose_name_plural = "запросы «Моя домашка»"


class ContentRequest(models.Model):
    """Заявка на контент для родителя: ненайденная тема домашки."""

    STATUSES = [("new", "новая"), ("done", "сделано")]
    family = models.ForeignKey("accounts.Family", on_delete=models.CASCADE, related_name="content_requests")
    child = models.ForeignKey("accounts.ChildProfile", null=True, blank=True, on_delete=models.SET_NULL)
    text = models.CharField(max_length=200)
    source = models.CharField(max_length=10, default="homework")
    status = models.CharField(max_length=6, choices=STATUSES, default="new")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "заявка на контент"
        verbose_name_plural = "заявки на контент"
