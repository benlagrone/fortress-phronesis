#!/usr/bin/env python3
"""Benchmark installed Ollama chat models with non-private prompts."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from typing import Any


DEFAULT_PROMPT = "What is consciousness?"
DEFAULT_SYSTEM_PROMPT = "Answer clearly in one short sentence."


def _request_json(url: str, payload: dict[str, Any] | None = None, timeout: float = 30.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def _model_names(base_url: str, timeout: float) -> list[str]:
    payload = _request_json(f"{base_url.rstrip('/')}/api/tags", timeout=timeout)
    return [
        str(item.get("name"))
        for item in payload.get("models", [])
        if isinstance(item, dict) and item.get("name")
    ]


def _benchmark_model(
    base_url: str,
    model: str,
    system_prompt: str,
    prompt: str,
    num_predict: int,
    timeout: float,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": num_predict,
        },
    }
    start = time.monotonic()
    try:
        response = _request_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
        elapsed = time.monotonic() - start
        message = response.get("message") if isinstance(response, dict) else None
        content = str((message or {}).get("content") or "")
        return {
            "model": model,
            "ok": True,
            "seconds": round(elapsed, 3),
            "chars": len(content),
            "done_reason": response.get("done_reason"),
            "sample": content[:160],
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {
            "model": model,
            "ok": False,
            "seconds": round(time.monotonic() - start, 3),
            "error": type(exc).__name__,
            "detail": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11434", help="Ollama base URL")
    parser.add_argument("--models", default="", help="Comma-separated model names; defaults to /api/tags")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--num-predict", type=int, default=160)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    models = [item.strip() for item in args.models.split(",") if item.strip()]
    if not models:
        models = _model_names(args.base_url, args.timeout)

    for model in models:
        print(
            json.dumps(
                _benchmark_model(
                    base_url=args.base_url,
                    model=model,
                    system_prompt=args.system_prompt,
                    prompt=args.prompt,
                    num_predict=args.num_predict,
                    timeout=args.timeout,
                ),
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
