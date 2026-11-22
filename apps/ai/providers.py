"""Слой абстракции LLMProvider (раздел 9.5 ТЗ, D-101).

complete(messages, max_tokens, temperature) -> LLMResult(text, tokens_in, tokens_out, cost).
Gemini и OpenRouter работают через один OpenAI-совместимый HTTP-клиент (urllib, без новых зависимостей);
смена провайдера = смена base_url, ключа и модели в окружении. Вызовы только с сервера (CSP не меняется).
FakeProvider — офлайн-режим: без ключа, в тестах и при сбое сети. Сайт никогда не падает из-за ИИ.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from django.conf import settings


class LLMError(Exception):
    """Любая ошибка провайдера: сеть, таймаут, 4xx/5xx, регион, неожиданный ответ."""


@dataclass
class LLMResult:
    text: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    provider: str = ""
    model: str = ""


def _cfg() -> dict:
    return getattr(settings, "AI", {}) or {}


def _cost(tokens_in: int, tokens_out: int) -> float:
    c = _cfg()
    return tokens_in * float(c.get("PRICE_IN_PER_M", 0.30)) / 1e6 + tokens_out * float(c.get("PRICE_OUT_PER_M", 2.50)) / 1e6


class LLMProvider:
    name = "base"
    offline = False
    model = ""

    def complete(self, messages: list[dict], max_tokens: int = 400, temperature: float = 0.3) -> LLMResult:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """POST {base_url}/chat/completions с Bearer-ключом. Подходит для Gemini и OpenRouter."""

    def __init__(self, name: str, base_url: str, api_key: str, model: str, *, timeout: float = 15,
                 proxy: str = "", extra_headers: dict | None = None, extra_body: dict | None = None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.proxy = proxy
        self.extra_headers = extra_headers or {}
        self.extra_body = extra_body or {}

    def _opener(self):
        if self.proxy:
            return urllib.request.build_opener(urllib.request.ProxyHandler({"https": self.proxy, "http": self.proxy}))
        return urllib.request.build_opener()

    def complete(self, messages, max_tokens=400, temperature=0.3) -> LLMResult:
        body = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
        body.update(self.extra_body)
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}", **self.extra_headers},
            method="POST",
        )
        data = None
        for attempt in (1, 2):  # один повтор при перегрузке (5xx/429) или обрыве сети
            try:
                with self._opener().open(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:  # тело ответа в лог не пишем (может содержать ключ)
                if attempt == 1 and (e.code >= 500 or e.code == 429):
                    time.sleep(1)
                    continue
                raise LLMError(f"{self.name}: HTTP {e.code}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                if attempt == 1:
                    time.sleep(1)
                    continue
                raise LLMError(f"{self.name}: {type(e).__name__}") from None
            except ValueError:
                raise LLMError(f"{self.name}: bad json") from None
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise LLMError(f"{self.name}: unexpected response") from None
        usage = data.get("usage") or {}
        t_in = int(usage.get("prompt_tokens") or 0)
        t_out = int(usage.get("completion_tokens") or 0)
        return LLMResult(text=text.strip(), tokens_in=t_in, tokens_out=t_out, cost=_cost(t_in, t_out),
                         provider=self.name, model=self.model)


class FakeProvider(LLMProvider):
    """Офлайн-провайдер: ничего не отправляет в сеть. Ответ собирают helper/feynman из материалов сайта.

    В тестах можно задать заранее ответы: FakeProvider(replies=["...", "..."]).
    """

    name = "offline"
    offline = True
    model = "offline"

    def __init__(self, replies: list[str] | None = None):
        self.replies = list(replies or [])
        self.calls: list[list[dict]] = []

    def complete(self, messages, max_tokens=400, temperature=0.3) -> LLMResult:
        self.calls.append(messages)
        if not self.replies:
            raise LLMError("offline: no reply")
        return LLMResult(text=self.replies.pop(0), provider=self.name, model=self.model)


_override: LLMProvider | None = None


def set_provider_for_tests(provider: LLMProvider | None) -> None:
    global _override
    _override = provider


def get_provider() -> LLMProvider:
    """AI_PROVIDER: gemini | openrouter | fake. Пусто — gemini при наличии GEMINI_API_KEY, иначе офлайн."""
    if _override is not None:
        return _override
    c = _cfg()
    name = (c.get("PROVIDER") or "").lower()
    if not name:
        name = "gemini" if c.get("GEMINI_API_KEY") else ("openrouter" if c.get("OPENROUTER_API_KEY") else "fake")
    extra_body = {}
    if c.get("REASONING_EFFORT"):
        extra_body["reasoning_effort"] = c["REASONING_EFFORT"]
    if name == "gemini" and c.get("GEMINI_API_KEY"):
        return OpenAICompatibleProvider(
            "gemini", c.get("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta/openai/",
            c["GEMINI_API_KEY"], c.get("MODEL") or "gemini-3.5-flash-lite",
            timeout=float(c.get("TIMEOUT", 15)), proxy=c.get("HTTPS_PROXY", ""), extra_body=extra_body,
        )
    if name == "openrouter" and c.get("OPENROUTER_API_KEY"):
        model = c.get("OPENROUTER_MODEL") or "google/" + (c.get("MODEL") or "gemini-3.5-flash-lite")
        return OpenAICompatibleProvider(
            "openrouter", c.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
            c["OPENROUTER_API_KEY"], model, timeout=float(c.get("TIMEOUT", 15)), proxy=c.get("HTTPS_PROXY", ""),
            extra_headers={"X-Title": "School site"}, extra_body=extra_body,
        )
    return FakeProvider()
