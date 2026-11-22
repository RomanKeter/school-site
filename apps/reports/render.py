"""Карточка недельного отчёта: HTML → PNG 1080×1350 через уже установленный Chrome. Без новых зависимостей."""
from __future__ import annotations

import logging
import subprocess
import tempfile
import time
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string

log = logging.getLogger(__name__)

WIDTH, HEIGHT = 1080, 1350


def _chrome_bin() -> str:
    cfg = getattr(settings, "TELEGRAM_REPORT", {})
    return cfg.get("CHROME", "/usr/bin/google-chrome")


def html_for_card(context: dict) -> str:
    return render_to_string("reports/weekly_card.html", context)


def render_png(html: str, chrome: str | None = None) -> bytes:
    """Рендерит HTML в PNG 1080×1350. Цель по ТЗ — ≤ 5 с; холодный старт может быть чуть дольше (пишем в лог)."""
    chrome = chrome or _chrome_bin()
    with tempfile.TemporaryDirectory(prefix="tg-report-") as tmp:
        tmp = Path(tmp)
        src = tmp / "card.html"
        out = tmp / "card.png"
        src.write_text(html, encoding="utf-8")
        cmd = [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            f"--window-size={WIDTH},{HEIGHT}",
            f"--screenshot={out}",
            src.resolve().as_uri(),
        ]
        t0 = time.monotonic()
        proc = subprocess.run(cmd, capture_output=True, timeout=20)
        elapsed = time.monotonic() - t0
        if elapsed > 5:
            log.warning("Генерация карточки заняла %.2f с (цель ≤ 5 с)", elapsed)
        else:
            log.info("Генерация карточки: %.2f с", elapsed)
        if proc.returncode != 0 or not out.exists():
            err = (proc.stderr or b"").decode(errors="replace")[-400:]
            raise RuntimeError(f"Chrome не собрал карточку (код {proc.returncode}): {err}")
        data = out.read_bytes()
    return data
