#!/usr/bin/env python3
"""Production smoke check for the public PericopeAI API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_REQUIRED_AUTHOR_SLUGS = (
    "augustine,"
    "eusebius_pamphilus,"
    "john_chrysostom,"
    "machiavelli,"
    "epictetus,"
    "seneca,"
    "musonius_rufus,"
    "hermes_trismegistus,"
    "athanasius_of_alexandria,"
    "origen_of_alexandria,"
    "cyprian_of_carthage,"
    "boethius,"
    "anselm_of_canterbury"
)


class SmokeFailure(RuntimeError):
    """Raised when a production smoke contract fails."""


def _csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _read_api_key(env_file: str) -> str:
    for env_name in ("PERICOPE_API_KEY", "AUGUSTINE_API_KEY"):
        value = os.getenv(env_name, "").strip()
        if value:
            return value

    values: dict[str, str] = {}
    if env_file:
        path = Path(env_file)
        if not path.is_file():
            raise SmokeFailure(f"API key env file does not exist: {path}")
        values = _parse_env_file(path)

    api_keys = values.get("AUGUSTINE_API_KEYS", "")
    if api_keys:
        keys = _csv_list(api_keys)
        if keys:
            return keys[0]

    frontend_key = values.get("REACT_APP_AUGUSTINE_API_KEY", "").strip()
    if frontend_key:
        return frontend_key

    raise SmokeFailure(
        "Missing API key. Set PERICOPE_API_KEY/AUGUSTINE_API_KEY or pass "
        "--env-file containing AUGUSTINE_API_KEYS."
    )


def _request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    api_key: str | None = None,
    timeout: int = 30,
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {
        "Accept": "application/json",
        "User-Agent": "fortress-phronesis-prod-smoke/1.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    if api_key:
        headers["X-API-Key"] = api_key

    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise SmokeFailure(f"{method} {url} failed: HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise SmokeFailure(f"{method} {url} failed: {exc!r}") from exc

    try:
        return json.loads(response_body)
    except Exception as exc:
        raise SmokeFailure(f"{method} {url} returned invalid JSON: {exc}") from exc


def _api_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _segment_payloads(segments: list[Any]) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_type = str(segment.get("type") or "")
        payload = segment.get("payload")
        payloads[segment_type] = payload if isinstance(payload, dict) else {}
    return payloads


def _check_health(payload: Any) -> None:
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        raise SmokeFailure(f"health payload is not ok: {payload!r}")
    db = payload.get("db")
    if isinstance(db, dict) and db.get("ok") is not True:
        raise SmokeFailure(f"database health is not ok: {payload!r}")


def _check_authors(payload: Any, *, required_slugs: list[str], min_visible_authors: int) -> int:
    if not isinstance(payload, list):
        raise SmokeFailure("/v1/authors did not return a list")
    slugs = {
        str(author.get("slug") or "").strip()
        for author in payload
        if isinstance(author, dict) and str(author.get("slug") or "").strip()
    }
    if len(slugs) < min_visible_authors:
        raise SmokeFailure(
            f"visible author count {len(slugs)} is below minimum {min_visible_authors}"
        )
    missing = sorted(set(required_slugs) - slugs)
    if missing:
        raise SmokeFailure(f"required authors missing from /v1/authors: {', '.join(missing)}")
    return len(slugs)


def _check_chat(payload: Any, *, args: argparse.Namespace) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SmokeFailure("/v2/chat did not return an object")
    if payload.get("status") != "done":
        raise SmokeFailure(f"/v2/chat status is not done: {payload.get('status')!r}")
    if payload.get("persona") != args.persona:
        raise SmokeFailure(f"/v2/chat persona mismatch: {payload.get('persona')!r}")

    segments = payload.get("segments")
    if not isinstance(segments, list):
        raise SmokeFailure("/v2/chat response has no segments list")
    segment_types = [str(segment.get("type") or "") for segment in segments if isinstance(segment, dict)]
    missing_segments = sorted(set(args.required_segments) - set(segment_types))
    if missing_segments:
        raise SmokeFailure(f"/v2/chat missing segments: {', '.join(missing_segments)}")

    by_type = _segment_payloads(segments)
    answer = str(by_type.get("answer", {}).get("answer") or "")
    summary = str(by_type.get("summary", {}).get("summary") or "")
    citations = by_type.get("citations", {}).get("citations")
    books = by_type.get("books", {}).get("books")
    metadata = payload.get("metadata")

    if len(answer) < args.min_answer_chars:
        raise SmokeFailure(f"answer too short: {len(answer)} chars")
    if len(summary) < args.min_summary_chars:
        raise SmokeFailure(f"summary too short: {len(summary)} chars")
    if not isinstance(citations, list) or len(citations) < args.min_citations:
        raise SmokeFailure(f"citation count below minimum {args.min_citations}")
    if not isinstance(books, list) or len(books) < args.min_books:
        raise SmokeFailure(f"book count below minimum {args.min_books}")
    if not isinstance(metadata, list) or len(metadata) < args.min_metadata:
        raise SmokeFailure(f"metadata count below minimum {args.min_metadata}")

    return {
        "status": payload.get("status"),
        "persona": payload.get("persona"),
        "mode": payload.get("mode"),
        "session_id": payload.get("session_id"),
        "segment_types": segment_types,
        "answer_chars": len(answer),
        "summary_chars": len(summary),
        "citations": len(citations),
        "books": len(books),
        "metadata": len(metadata),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a public PericopeAI production smoke check.")
    parser.add_argument("--api-base-url", default="https://pericopeai.com/api")
    parser.add_argument("--env-file", default="", help="Optional service .env file with AUGUSTINE_API_KEYS")
    parser.add_argument("--persona", default="augustine")
    parser.add_argument("--mode", default="conversation")
    parser.add_argument("--question", default="In one brief paragraph, what is wisdom?")
    parser.add_argument("--session-id", default="")
    parser.add_argument("--user-id", default="prod-smoke")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--required-slugs", default=DEFAULT_REQUIRED_AUTHOR_SLUGS)
    parser.add_argument("--min-visible-authors", type=int, default=70)
    parser.add_argument("--required-segments", nargs="+", default=["answer", "citations", "summary", "books"])
    parser.add_argument("--min-answer-chars", type=int, default=40)
    parser.add_argument("--min-summary-chars", type=int, default=20)
    parser.add_argument("--min-citations", type=int, default=1)
    parser.add_argument("--min-books", type=int, default=1)
    parser.add_argument("--min-metadata", type=int, default=1)
    args = parser.parse_args()

    session_id = args.session_id or (
        "prod-smoke-"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )

    try:
        api_key = _read_api_key(args.env_file)
        health_payload = _request_json(
            _api_url(args.api_base_url, "/healthz"),
            timeout=args.timeout,
        )
        _check_health(health_payload)

        authors_payload = _request_json(
            _api_url(args.api_base_url, "/v1/authors"),
            timeout=args.timeout,
        )
        visible_authors = _check_authors(
            authors_payload,
            required_slugs=_csv_list(args.required_slugs),
            min_visible_authors=args.min_visible_authors,
        )

        chat_payload = _request_json(
            _api_url(args.api_base_url, "/v2/chat"),
            method="POST",
            payload={
                "question": args.question,
                "mode": args.mode,
                "persona": args.persona,
                "session_id": session_id,
                "user_id": args.user_id,
                "follow_up_question_enabled": False,
            },
            api_key=api_key,
            timeout=args.timeout,
        )
        chat_summary = _check_chat(chat_payload, args=args)
    except SmokeFailure as exc:
        sys.stderr.write(f"Pericope production smoke failed: {exc}\n")
        return 1

    print(
        json.dumps(
            {
                "ok": True,
                "api_base_url": args.api_base_url.rstrip("/"),
                "visible_authors": visible_authors,
                **chat_summary,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
