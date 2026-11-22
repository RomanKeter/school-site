"""Резолвер текущего шага блока → контекст для шаблона."""
from __future__ import annotations

from apps.content.models import Exercise, Skill, VocabularyWord
from apps.srs.models import ReviewItem

from .adaptive import AdaptiveState, pick_difficulty
from .models import Block


def current_step(block: Block):
    if block.position >= len(block.queue):
        return None
    return block.queue[block.position]


def resolve(block: Block):
    step = current_step(block)
    if step is None:
        return {"kind": "done"}
    t = step.get("t")
    if t == "celebrate":
        return {"kind": "celebrate"}
    if t == "worked":
        skill = Skill.objects.get(pk=step["skill"])
        return {"kind": "worked", "skill": skill, "example": skill.worked_example or {}}
    if t == "ex":
        ex = Exercise.objects.get(pk=step["id"])
        return {"kind": "exercise", "exercise": ex, "stage": step.get("stage", "solo")}
    if t == "adaptive":
        skill = Skill.objects.get(pk=step["skill"])
        level = int(block.meta.get("level", 1))
        prefer = step.get("prefer")
        ex = None
        if prefer:
            ex = Exercise.objects.filter(pk=prefer, skill=skill).first()
        if ex is None:
            qs = Exercise.objects.filter(skill=skill, status="published")
            d = pick_difficulty(set(qs.values_list("difficulty", flat=True)), level)
            ex = qs.filter(difficulty=d).order_by("?").first() if d else None
        if ex is None:
            return {"kind": "skip"}
        return {"kind": "exercise", "exercise": ex, "stage": step.get("stage", "solo"), "adaptive": True}
    if t == "word":
        word = VocabularyWord.objects.get(pk=step["id"])
        return {"kind": "word", "word": word, "mode": step.get("mode", "flashcard")}
    if t == "review":
        item = ReviewItem.objects.select_related("skill", "word", "exercise").get(pk=step["item"])
        if item.word_id:
            # чередование направлений по reviews_count
            modes = ["picture_choice", "tiles", "ru_to_en", "en_to_ru"]
            mode = modes[item.reviews_count % len(modes)]
            return {"kind": "word", "word": item.word, "mode": mode, "review_item": item}
        skill = item.skill or (item.exercise.skill if item.exercise_id else None)
        if item.exercise_id:
            return {"kind": "exercise", "exercise": item.exercise, "stage": "review", "review_item": item}
        qs = Exercise.objects.filter(skill=skill, status="published")
        level = int(block.meta.get("level", 1))
        d = pick_difficulty(set(qs.values_list("difficulty", flat=True)), level)
        ex = qs.filter(difficulty=d).order_by("?").first() if d else qs.order_by("?").first()
        return {"kind": "exercise", "exercise": ex, "stage": "review", "review_item": item, "skill": skill}
    return {"kind": "skip"}
