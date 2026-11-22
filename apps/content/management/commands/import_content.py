"""Импорт контента из JSON (раздел 12.3)."""
from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.content.models import Exercise, Skill, Subject, Topic, Unit


class Command(BaseCommand):
    help = "import_content path/to/file.json [--dry-run] [--update]"

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--update", action="store_true")

    def handle(self, path, dry_run, update, **kw):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("format_version") != 1:
            raise CommandError("format_version должен быть 1")
        # D-504: один файл может содержать несколько юнитов в ключе "units".
        items = data["units"] if "units" in data else [data]
        report = {"created": 0, "updated": 0, "errors": []}
        try:
            with transaction.atomic():
                for item in items:
                    self._import(item, update, report)
                if report["errors"]:
                    raise _HasErrors()
                if dry_run:
                    raise _DryRun()
        except _DryRun:
            self.stdout.write(self.style.WARNING(
                f"dry-run: ошибок нет, было бы создано {report['created']}, обновлено {report['updated']}. В БД ничего не записано."))
            return
        except _HasErrors:
            pass
        if report["errors"]:
            for e in report["errors"]:
                self.stderr.write(self.style.ERROR(e))
            raise CommandError(f"Ошибок: {len(report['errors'])}")
        self.stdout.write(self.style.SUCCESS(
            f"Создано {report['created']}, обновлено {report['updated']}"
        ))

    def _import(self, data, update, report):
        subj_code = data["subject"]
        subject, _ = Subject.objects.get_or_create(
            code=subj_code,
            defaults={"title": {"math": "Математика", "en": "Английский", "ru": "Русский язык", "cim": "Человек и мир"}.get(subj_code, subj_code),
                      "color_token": subj_code, "icon": {"math": "🔢", "cim": "🌍", "ru": "📝"}.get(subj_code, "🔤")},
        )
        u = data["unit"]
        unit = self._upsert(Unit, u["key"], update, report,
                            subject=subject, title=u["title"], grade=u.get("grade", 5),
                            quarter=u.get("quarter", 1), order=u.get("order", 0), status="published")
        for ti, t in enumerate(data.get("topics", [])):
            topic = self._upsert(Topic, t["key"], update, report,
                                 unit=unit, title=t["title"], description=t.get("description", ""),
                                 synonyms=t.get("synonyms", []), keywords=t.get("keywords", []),
                                 textbook_refs=t.get("textbook_refs", []),
                                 badge_code=t.get("badge_code", ""), order=t.get("order", ti), status="published")
            for si, s in enumerate(t.get("skills", [])):
                skill = self._upsert(Skill, s["key"], update, report,
                                     topic=topic, title=s["title"], description=s.get("description", ""),
                                     rule_card=s.get("rule_card", ""), worked_example=s.get("worked_example", {}),
                                     order=s.get("order", si), status="published")
                for pk in s.get("prerequisites", []):
                    pre = Skill.objects.filter(external_key=pk).first()
                    if pre:
                        skill.prerequisites.add(pre)
                    else:
                        report["errors"].append(f"prerequisite not found: {pk}")
                for ei, e in enumerate(s.get("exercises", [])):
                    if "type" not in e or "answer" not in e:
                        report["errors"].append(f"topics[{ti}].skills[{si}].exercises[{ei}] ({e.get('key', '?')}): type/answer required")
                        continue
                    self._upsert(Exercise, e["key"], update, report,
                                 skill=skill, type=e["type"], difficulty=e.get("difficulty", 1),
                                 payload=e.get("payload", {}), answer=e["answer"],
                                 est_seconds=e.get("est_seconds", 40),
                                 is_template=e.get("template", False),
                                 tags=e.get("tags", []), status="published")
            for wi, w in enumerate(t.get("words", [])):
                from apps.content.models import VocabularyWord
                self._upsert(VocabularyWord, w["key"], update, report,
                             language=w.get("language", "en"), word=w["word"],
                             translation_ru=w["translation_ru"], transcription=w.get("transcription", ""),
                             example=w.get("example", ""), example_translation=w.get("example_translation", ""),
                             picture=w.get("picture", ""), topic=topic, order=w.get("order", wi),
                             status="published")

    def _upsert(self, model, key, update, report, **fields):
        obj = model.objects.filter(external_key=key).first()
        if obj:
            if not update:
                report["errors"].append(f"duplicate key without --update: {key}")
                return obj
            for k, v in fields.items():
                setattr(obj, k, v)
            obj.save()
            report["updated"] += 1
            return obj
        obj = model.objects.create(external_key=key, **fields)
        report["created"] += 1
        return obj


class _DryRun(Exception):
    pass


class _HasErrors(Exception):
    pass
