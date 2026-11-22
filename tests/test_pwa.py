"""Этап 2: офлайн-режим PWA (раздел 23.5 ТЗ, D-700+). Сеть наружу не используется."""
import json
import uuid

import pytest
from django.urls import reverse

from apps.learning.models import Attempt, SyncConflict
from apps.learning.offline import MAX_PACKAGE_BYTES, build_package, sync_item
from tests.test_integration import login_child


def test_package_today_and_tomorrow(client, family, content):
    parent, child = family
    login_child(client, child)
    r = client.get("/offline/package/")
    assert r.status_code == 200
    pkg = r.json()
    assert len(pkg["days"]) == 2
    assert pkg["size_bytes"] <= MAX_PACKAGE_BYTES
    assert pkg["child"]["id"] == child.pk
    assert "quiet_from" in pkg["child"]["settings"]
    assert "/homework/" in pkg["needs_net"]
    # в пакете есть ответы только для заданий миссии (исключение из FR-LRN-2)
    if pkg["exercises"]:
        ex = next(iter(pkg["exercises"].values()))
        assert "answer" in ex and "type" in ex


def test_sync_idempotent_and_recheck(client, family, content):
    parent, child = family
    login_child(client, child)
    pkg = build_package(child)
    assert pkg["exercises"] or pkg["words"]
    if pkg["exercises"]:
        eid, ex = next(iter(pkg["exercises"].items()))
        item = {
            "client_uuid": str(uuid.uuid4()),
            "client_created_at": "2026-11-22T12:00:00+03:00",
            "block_id": pkg["days"][0]["blocks"][0]["id"] if pkg["days"][0]["blocks"] else None,
            "exercise_id": int(eid),
            "answer": ex["answer"] or {},
            "attempt_no": 1,
            "hints_used": 0,
            "duration_ms": 800,
            "client_correct": True,
            "client_final": True,
            "context": "mission",
        }
    else:
        wid, word = next(iter(pkg["words"].items()))
        item = {
            "client_uuid": str(uuid.uuid4()),
            "client_created_at": "2026-11-22T12:00:00+03:00",
            "word_id": int(wid),
            "word_mode": "en_to_ru",
            "answer": {"value": word["translation_ru"]},
            "attempt_no": 1,
            "client_correct": True,
            "client_final": True,
            "context": "words",
        }
    r = client.post("/offline/sync/", data=json.dumps({"items": [item]}), content_type="application/json")
    assert r.status_code == 200 and r.json()["ok"] and not r.json()["results"][0]["duplicate"]
    uid = item["client_uuid"]
    assert Attempt.objects.filter(client_uuid=uid, offline=True).count() == 1
    # повтор не создаёт дубль
    r2 = client.post("/offline/sync/", data=json.dumps({"items": [item]}), content_type="application/json")
    assert r2.json()["results"][0]["duplicate"] is True
    assert Attempt.objects.filter(client_uuid=uid).count() == 1


def test_sync_logs_conflict(family, content):
    parent, child = family
    pkg = build_package(child)
    assert pkg["exercises"], "нужно задание в миссии"
    eid, ex = next(iter(pkg["exercises"].items()))
    item = {
        "client_uuid": str(uuid.uuid4()),
        "exercise_id": int(eid),
        "answer": {"value": "__definitely_wrong__"},
        "attempt_no": 1,
        "client_correct": True,  # клиент ошибся в проверке
        "client_final": True,
        "context": "mission",
    }
    out = sync_item(child, item)
    assert out["ok"] and out["is_correct"] is False
    assert SyncConflict.objects.filter(attempt_id=out["attempt_id"]).exists()


def test_manifest_and_service_worker(client):
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Учимся с Масей" and data["start_url"] == "/home/" and data["display"] == "standalone"
    sw = client.get("/sw.js")
    assert sw.status_code == 200
    assert sw["Service-Worker-Allowed"] == "/"
    body = b"".join(sw.streaming_content) if hasattr(sw, "streaming_content") else sw.content
    assert b"masya-shell" in body


def test_package_requires_child(client, family):
    parent, child = family
    assert client.get("/offline/package/").status_code == 302
    client.force_login(parent.user)
    assert client.get("/offline/package/").status_code == 302  # не ребёнок
