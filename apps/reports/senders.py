"""Отправка в Telegram. Токен — только TELEGRAM_REPORT_BOT_TOKEN, никогда TELEGRAM_BOT_TOKEN."""
from __future__ import annotations

import json
import logging
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

log = logging.getLogger(__name__)

# Повтор при ошибке 3 раза с паузой 1/5/15 мин (TG-5). В тестах подменяют delays и sleeper.
RETRY_DELAYS = (60, 300, 900)
TELEGRAM_API = "https://api.telegram.org"


class SendError(Exception):
    """Ошибка отправки (текст не содержит токен)."""


class TransientError(SendError):
    """Сеть / 5xx / 429 — можно повторить."""


class FakeSender:
    """Подставной отправитель для тестов: ничего не шлёт в сеть, копит сообщения."""

    def __init__(self):
        self.sent = []

    def send_message(self, chat_id: str, text: str) -> dict:
        rec = {"type": "message", "chat_id": str(chat_id), "text": text}
        self.sent.append(rec)
        return rec

    def send_photo(self, chat_id: str, photo: bytes, caption: str = "") -> dict:
        rec = {"type": "photo", "chat_id": str(chat_id), "caption": caption, "photo": photo}
        self.sent.append(rec)
        return rec


def _redact(text: str, token: str) -> str:
    if token and token in text:
        return text.replace(token, "[token]")
    return text


def _multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    crlf = b"\r\n"
    chunks = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n".encode() + str(value).encode() + crlf)
    for name, (filename, content_type, data) in files.items():
        head = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode()
        chunks.append(head + data + crlf)
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


class TelegramSender:
    """Реальная отправка через Bot API. Токен только из TELEGRAM_REPORT_BOT_TOKEN."""

    def __init__(self, token: str | None = None, delays=RETRY_DELAYS, sleeper=time.sleep, api_base: str | None = None):
        cfg = getattr(settings, "TELEGRAM_REPORT", {})
        self.token = token if token is not None else cfg.get("BOT_TOKEN", "")
        self.delays = delays
        self.sleeper = sleeper
        self.api_base = (api_base or TELEGRAM_API).rstrip("/")
        if not self.token:
            raise SendError("Не задан TELEGRAM_REPORT_BOT_TOKEN")

    def _url(self, method: str) -> str:
        return f"{self.api_base}/bot{self.token}/{method}"

    def _request(self, method: str, fields: dict, files: dict | None = None) -> dict:
        def once():
            if files:
                body, ctype = _multipart(fields, files)
            else:
                body = json.dumps(fields).encode()
                ctype = "application/json"
            req = Request(self._url(method), data=body, method="POST", headers={"Content-Type": ctype})
            try:
                with urlopen(req, timeout=20) as resp:
                    raw = resp.read()
            except HTTPError as e:
                raw = e.read() if e.fp else b""
                msg = _redact(f"HTTP {e.code} {raw[:200]!r}", self.token)
                if e.code in (429, 500, 502, 503, 504) or e.code >= 500:
                    raise TransientError(msg) from None
                raise SendError(msg) from None
            except URLError as e:
                raise TransientError(_redact(f"сеть: {e.reason}", self.token)) from None
            try:
                data = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                raise SendError("Ответ Telegram не JSON") from None
            if not data.get("ok"):
                desc = _redact(str(data.get("description", "ошибка API")), self.token)
                raise SendError(desc)
            return data

        last = None
        attempts = [0, *self.delays]
        for i, wait in enumerate(attempts):
            if wait:
                self.sleeper(wait)
            try:
                return once()
            except TransientError as e:
                last = e
                log.warning("Telegram: временная ошибка, попытка %s/%s", i + 1, len(attempts))
        raise last

    def send_message(self, chat_id: str, text: str) -> dict:
        return self._request("sendMessage", {"chat_id": chat_id, "text": text})

    def send_photo(self, chat_id: str, photo: bytes, caption: str = "") -> dict:
        fields = {"chat_id": chat_id, "caption": caption}
        files = {"photo": ("report.png", "image/png", photo)}
        return self._request("sendPhoto", fields, files)


def get_sender():
    """Реальный отправитель при наличии токена, иначе FakeSender (dev/тесты)."""
    token = getattr(settings, "TELEGRAM_REPORT", {}).get("BOT_TOKEN", "")
    if token:
        return TelegramSender(token)
    return FakeSender()
