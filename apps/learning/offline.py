"""Пакет дня и синхронизация офлайн-ответов (раздел 23.5 ТЗ, D-700+)."""
from __future__ import annotations

import datetime as dt
import json
import logging
import uuid
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.accounts.utils import local_today
from apps.content.models import Exercise, VocabularyWord
from apps.missions.builder import ensure_mission
from apps.missions.models import DailyMission

from .models import Attempt, Block, OfflinePackage, SyncConflict
from . import services

log = logging.getLogger(__name__)

MAX_PACKAGE_BYTES = 15 * 1024 * 1024

SHELL_ASSETS = [
    "/static/css/app.css",
    "/static/js/app.js",
    "/static/js/htmx.min.js",
    "/static/js/pwa.js",
    "/static/js/sw.js",
    "/static/favicon.svg",
    "/static/img/mascot/zubrik-hello.svg",
    "/static/img/mascot/zubrik-hint.svg",
    "/static/img/mascot/zubrik-party.svg",
    "/static/img/mascot/zubrik-think.svg",
    "/static/img/mascot/zubrik-rest.svg",
    "/static/fonts/manrope-cyrillic-500-normal.woff2",
    "/static/fonts/manrope-cyrillic-700-normal.woff2",
    "/static/fonts/manrope-cyrillic-800-normal.woff2",
    "/static/fonts/manrope-latin-500-normal.woff2",
    "/static/fonts/manrope-latin-700-normal.woff2",
    "/static/fonts/manrope-latin-800-normal.woff2",
]


def _settings_payload(child) -> dict:
    s = child.settings
    return {
        "quiet_from": s.quiet_from.strftime("%H:%M") if s.quiet_from else "",
        "quiet_to": s.quiet_to.strftime("%H:%M") if s.quiet_to else "",
        "daily_limit_min": s.daily_limit_min,
        "break_every_min": s.break_every_min,
        "days_off": list(s.days_off or []),
    }


def _exercise_payload(ex: Exercise) -> dict:
    payload = ex.payload or {}
    return {
        "id": ex.id,
        "type": ex.type,
        "payload": payload,
        "answer": ex.answer or {},
        "hints": payload.get("hints") or [],
        "skill_id": ex.skill_id,
        "est_seconds": ex.est_seconds,
    }


def _word_payload(word: VocabularyWord) -> dict:
    slug = "".join(ch if ch.isalnum() else "_" for ch in (word.word or "").lower())
    image = f"/static/img/words/{slug}.svg"
    return {
        "id": word.id,
        "word": word.word,
        "translation_ru": word.translation_ru,
        "transcription": word.transcription,
        "picture": word.picture or "",
        "image": image,
        "example": word.example,
    }


def build_package(child, today: dt.date | None = None) -> dict:
    today = today or local_today(child.family)
    days = []
    exercises, words, assets = {}, {}, list(SHELL_ASSETS)
    for i, day in enumerate((today, today + dt.timedelta(days=1))):
        mission = ensure_mission(child, today=day)
        blocks = []
        for b in mission.blocks.all().order_by("order"):
            blocks.append({
                "id": b.id,
                "title": b.title,
                "kind": b.kind,
                "queue": b.queue,
                "position": b.position,
                "status": b.status,
                "play_url": f"/play/{b.id}/",
            })
            for step in b.queue or []:
                if step.get("t") == "ex" and step.get("id"):
                    ex = Exercise.objects.filter(pk=step["id"]).first()
                    if ex:
                        exercises[str(ex.id)] = _exercise_payload(ex)
                if step.get("t") == "word" and step.get("id"):
                    w = VocabularyWord.objects.filter(pk=step["id"]).first()
                    if w:
                        words[str(w.id)] = _word_payload(w)
                        assets.append(f"/static/img/words/{''.join(ch if ch.isalnum() else '_' for ch in (w.word or '').lower())}.svg")
        days.append({"date": day.isoformat(), "mission_id": mission.id, "status": mission.status, "blocks": blocks})
    pkg = {
        "version": 1,
        "generated_at": timezone.now().isoformat(),
        "child": {"id": child.pk, "name": child.display_name, "settings": _settings_payload(child)},
        "days": days,
        "exercises": exercises,
        "words": words,
        "assets": sorted(set(assets)),
        "needs_net": ["/homework/", "/ai/teach/", "/parent/"],
    }
    raw = json.dumps(pkg, ensure_ascii=False, separators=(",", ":"))
    size = len(raw.encode())
    pkg["size_bytes"] = size
    if size > MAX_PACKAGE_BYTES:
        log.warning("Офлайн-пакет %s байт > 15 МБ", size)
    rec, _ = OfflinePackage.objects.update_or_create(
        child=child, date=today,
        defaults={"version": pkg["version"], "size_bytes": size},
    )
    pkg["package_id"] = rec.pk
    return pkg


def mark_downloaded(child, today: dt.date | None = None):
    today = today or local_today(child.family)
    OfflinePackage.objects.filter(child=child, date=today).update(downloaded_at=timezone.now())


def sync_item(child, item: dict) -> dict:
    """Принимает один офлайн-ответ. Идемпотентно по client_uuid. Сервер перепроверяет ответ."""
    raw_uuid = item.get("client_uuid") or ""
    try:
        client_uuid = uuid.UUID(str(raw_uuid))
    except (ValueError, TypeError, AttributeError):
        return {"ok": False, "error": "нужен client_uuid"}
    existing = Attempt.objects.filter(client_uuid=client_uuid).first()
    if existing:
        return {"ok": True, "duplicate": True, "attempt_id": existing.pk, "is_correct": existing.is_correct}

    exercise = word = block = None
    if item.get("exercise_id"):
        exercise = Exercise.objects.filter(pk=item["exercise_id"]).first()
    if item.get("word_id"):
        word = VocabularyWord.objects.filter(pk=item["word_id"]).first()
    if item.get("block_id"):
        block = Block.objects.filter(pk=item["block_id"], child=child).first()
    if not exercise and not word:
        return {"ok": False, "error": "нет задания"}

    given = item.get("answer") or {}
    if not isinstance(given, dict):
        given = {"value": given}
    created = parse_datetime(item.get("client_created_at") or "") or timezone.now()
    if timezone.is_naive(created):
        created = timezone.make_aware(created)

    att, fb = services.submit_answer(
        child,
        exercise=exercise,
        word=word,
        word_mode=item.get("word_mode") or "",
        block=block,
        given=given,
        attempt_no=int(item.get("attempt_no") or 1),
        hints_used=int(item.get("hints_used") or 0),
        duration_ms=int(item.get("duration_ms") or 0),
        context=item.get("context") or (block.kind if block else "mission"),
        solution_shown=bool(item.get("solution_shown")),
        final_now=bool(item.get("client_final")) and not exercise,  # не форсируем для обычных заданий
        client_uuid=client_uuid,
        client_created_at=created,
        offline=True,
    )
    client_correct = item.get("client_correct")
    if client_correct is not None and bool(client_correct) != bool(att.is_correct):
        SyncConflict.objects.create(
            attempt=att,
            client_result={"correct": client_correct, "answer": given},
            server_result={"correct": att.is_correct, "partial": att.partial_score},
        )
    return {"ok": True, "duplicate": False, "attempt_id": att.pk, "is_correct": att.is_correct, "is_final": att.is_final, "stars": fb.get("stars", 0)}


def sync_batch(child, items: list) -> dict:
    results = [sync_item(child, it) for it in items]
    return {"ok": all(r.get("ok") for r in results), "results": results}
