"""Tiny client for the local Ollama /api/chat endpoint.

Gemma 4 takes images *and* audio through the same `images` field, so one helper
covers photos of letters and spoken questions.
"""

import base64
import functools
import json
import time
from dataclasses import dataclass

import httpx

from . import config


@dataclass
class ChatResult:
    text: str
    seconds: float
    prompt_tokens: int
    output_tokens: int

    def as_json(self):
        return json.loads(self.text)


class OllamaError(RuntimeError):
    pass


def _b64(blob: bytes) -> str:
    return base64.b64encode(blob).decode("ascii")


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    schema: dict | None = None,
    temperature: float = 0.1,
    num_ctx: int = 16384,
    extra: dict | None = None,
) -> ChatResult:
    """Send one non-streaming chat request. `messages[i]["media"]` may hold raw bytes."""
    payload_msgs = []
    for m in messages:
        m = dict(m)
        media = m.pop("media", None)
        if media:
            m["images"] = [_b64(b) for b in media]
        payload_msgs.append(m)

    body = {
        "model": model or config.MODEL,
        "messages": payload_msgs,
        "stream": False,
        "think": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx, **(extra or {})},
        "keep_alive": "30m",
    }
    if schema:
        body["format"] = schema

    started = time.perf_counter()
    try:
        r = httpx.post(f"{config.OLLAMA_URL}/api/chat", json=body, timeout=config.REQUEST_TIMEOUT)
    except httpx.HTTPError as e:
        raise OllamaError(f"Can't reach Ollama at {config.OLLAMA_URL}: {e}") from e
    if r.status_code != 200:
        raise OllamaError(f"Ollama returned {r.status_code}: {r.text[:300]}")
    data = r.json()
    return ChatResult(
        text=data["message"]["content"],
        seconds=time.perf_counter() - started,
        prompt_tokens=data.get("prompt_eval_count", 0),
        output_tokens=data.get("eval_count", 0),
    )


@functools.lru_cache(maxsize=8)
def capabilities(model: str) -> frozenset:
    r = httpx.post(f"{config.OLLAMA_URL}/api/show", json={"model": model}, timeout=10)
    r.raise_for_status()
    return frozenset(r.json().get("capabilities", []))


def model_status(model: str | None = None) -> dict:
    """Is Ollama up, is the model pulled, and can it see and hear?"""
    model = model or config.MODEL
    try:
        r = httpx.post(f"{config.OLLAMA_URL}/api/show", json={"model": model}, timeout=10)
    except httpx.HTTPError:
        return {"ok": False, "model": model, "problem": "ollama_unreachable"}
    if r.status_code != 200:
        return {"ok": False, "model": model, "problem": "model_missing"}
    caps = r.json().get("capabilities", [])
    ear = model if "audio" in caps else config.EAR_MODEL
    try:
        hears = "audio" in capabilities(ear)
    except httpx.HTTPError:
        hears = False
    return {
        "ok": "vision" in caps,
        "model": model,
        "vision": "vision" in caps,
        "audio": hears,
        "ear_model": ear if hears else None,
        "problem": None if "vision" in caps else "model_cannot_see",
    }
