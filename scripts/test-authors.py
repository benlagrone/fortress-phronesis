#!/usr/bin/env python3
"""
Call the PericopeAI API for every author and record basic health metrics.

Outputs JSONL by default; use --format csv for CSV.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _request_json(url: str, payload: Optional[dict] = None, timeout: int = 60) -> Tuple[Optional[int], bytes, int, Optional[str]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    start = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return resp.status, body, elapsed_ms, None
    except urllib.error.HTTPError as e:
        body = e.read() if hasattr(e, "read") else b""
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return e.code, body, elapsed_ms, f"HTTPError {e.code}"
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return None, b"", elapsed_ms, repr(e)


def _parse_authors(body: bytes) -> List[dict]:
    try:
        data = json.loads(body.decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Failed to parse authors JSON: {e}") from e
    if not isinstance(data, list):
        raise RuntimeError("Authors response is not a list")
    return data


def _extract_answer(segments: Iterable[dict]) -> str:
    for seg in segments:
        if seg.get("type") == "answer":
            payload = seg.get("payload") or {}
            answer = payload.get("answer")
            if isinstance(answer, str):
                return answer
    return ""


def _extract_counts(segments: Iterable[dict]) -> Tuple[int, int]:
    citations_count = 0
    books_count = 0
    for seg in segments:
        if seg.get("type") == "citations":
            payload = seg.get("payload") or {}
            citations = payload.get("citations") or []
            if isinstance(citations, list):
                citations_count += len(citations)
        if seg.get("type") == "books":
            payload = seg.get("payload") or {}
            books = payload.get("books") or []
            if isinstance(books, list):
                books_count += len(books)
    return citations_count, books_count


def _position_stats(metadata: Iterable[dict]) -> Tuple[Optional[int], Optional[int]]:
    positions: List[int] = []
    for item in metadata:
        pos = item.get("position")
        if pos is None:
            continue
        try:
            positions.append(int(pos))
        except Exception:
            continue
    if not positions:
        return None, None
    return min(positions), max(positions)


def _write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test chat responses for all authors.")
    parser.add_argument("--base-url", default="http://localhost:18000", help="Pericope API base URL (default: http://localhost:18000)")
    parser.add_argument("--question", default="test", help="Question to ask each author")
    parser.add_argument("--mode", default="conversation", help="Chat mode (default: conversation)")
    parser.add_argument("--authors", default="", help="Comma-separated author slugs to test (default: all)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of authors tested")
    parser.add_argument("--timeout", type=int, default=120, help="HTTP timeout seconds")
    parser.add_argument(
        "--exclude-local-only",
        action="store_true",
        help="Exclude local_only authors when present",
    )
    parser.add_argument(
        "--min-answer-chars",
        type=int,
        default=200,
        help="Minimum answer length to pass (0 disables)",
    )
    parser.add_argument(
        "--min-citations",
        type=int,
        default=1,
        help="Minimum citation count to pass (0 disables)",
    )
    parser.add_argument(
        "--min-books",
        type=int,
        default=1,
        help="Minimum books count to pass (0 disables)",
    )
    parser.add_argument(
        "--min-metadata",
        type=int,
        default=1,
        help="Minimum metadata count to pass (0 disables)",
    )
    parser.add_argument(
        "--min-position-max",
        type=int,
        default=2,
        help="Minimum max(metadata.position) to pass (0 disables)",
    )
    parser.add_argument(
        "--max-elapsed-ms",
        type=int,
        default=0,
        help="Maximum elapsed_ms to pass (0 disables)",
    )
    parser.add_argument("--format", choices=["jsonl", "csv"], default="jsonl", help="Output format (default: jsonl)")
    parser.add_argument("--out", default="author-chat-test.jsonl", help="Output file path")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    authors_url = f"{base_url}/api/v1/authors"

    status, body, elapsed_ms, err = _request_json(authors_url, timeout=args.timeout)
    if status != 200:
        sys.stderr.write(f"Failed to fetch authors: status={status} err={err} body={body[:200]!r}\n")
        return 1

    authors = _parse_authors(body)
    if args.exclude_local_only:
        authors = [a for a in authors if not a.get("local_only")]

    selected = []
    if args.authors:
        allow = {s.strip().lower() for s in args.authors.split(",") if s.strip()}
        selected = [a for a in authors if str(a.get("slug", "")).lower() in allow]
    else:
        selected = authors

    if args.limit and args.limit > 0:
        selected = selected[: args.limit]

    results: List[Dict[str, Any]] = []
    total = len(selected)
    if total == 0:
        sys.stderr.write("No authors selected.\n")
        return 1

    for idx, author in enumerate(selected, start=1):
        slug = str(author.get("slug", "")).lower()
        sys.stderr.write(f"[{idx}/{total}] {slug}\n")

        payload = {"question": args.question, "mode": args.mode, "persona": slug}
        status, body, elapsed_ms, err = _request_json(f"{base_url}/api/v2/chat", payload=payload, timeout=args.timeout)

        row: Dict[str, Any] = {
            "author": slug,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "answer_chars": 0,
            "answer_words": 0,
            "citations": 0,
            "books": 0,
            "metadata": 0,
            "position_min": None,
            "position_max": None,
            "error": None,
            "pass": False,
            "fail_reasons": [],
            "response_bytes": len(body or b""),
        }

        if status != 200 or err:
            row["error"] = err or f"HTTP {status}"
            row["fail_reasons"].append(row["error"])
            results.append(row)
            continue

        try:
            resp = json.loads(body.decode("utf-8"))
        except Exception as e:
            row["error"] = f"JSON parse error: {e}"
            row["fail_reasons"].append(row["error"])
            results.append(row)
            continue

        segments = resp.get("segments") or []
        metadata = resp.get("metadata") or []
        answer = _extract_answer(segments)
        citations_count, books_count = _extract_counts(segments)
        pos_min, pos_max = _position_stats(metadata)

        row["answer_chars"] = len(answer)
        row["answer_words"] = len(answer.split())
        row["citations"] = citations_count
        row["books"] = books_count
        row["metadata"] = len(metadata) if isinstance(metadata, list) else 0
        row["position_min"] = pos_min
        row["position_max"] = pos_max
        if args.min_answer_chars > 0 and row["answer_chars"] < args.min_answer_chars:
            row["fail_reasons"].append(f"answer_chars<{args.min_answer_chars}")
        if args.min_citations > 0 and row["citations"] < args.min_citations:
            row["fail_reasons"].append(f"citations<{args.min_citations}")
        if args.min_books > 0 and row["books"] < args.min_books:
            row["fail_reasons"].append(f"books<{args.min_books}")
        if args.min_metadata > 0 and row["metadata"] < args.min_metadata:
            row["fail_reasons"].append(f"metadata<{args.min_metadata}")
        if args.min_position_max > 0:
            if row["position_max"] is None:
                row["fail_reasons"].append("position_max missing")
            elif row["position_max"] < args.min_position_max:
                row["fail_reasons"].append(f"position_max<{args.min_position_max}")
        if args.max_elapsed_ms > 0 and row["elapsed_ms"] > args.max_elapsed_ms:
            row["fail_reasons"].append(f"elapsed_ms>{args.max_elapsed_ms}")

        row["pass"] = not row["fail_reasons"]

        results.append(row)

    out_path = Path(args.out)
    if args.format == "csv":
        _write_csv(out_path, results)
    else:
        _write_jsonl(out_path, results)

    ok = sum(1 for r in results if r.get("pass"))
    errors = len(results) - ok
    avg_ms = int(sum(r["elapsed_ms"] for r in results) / max(1, len(results)))
    avg_chars = int(sum(r["answer_chars"] for r in results) / max(1, ok or 1))
    sys.stderr.write(
        f"Done. total={len(results)} ok={ok} errors={errors} avg_ms={avg_ms} avg_answer_chars={avg_chars}\n"
    )
    sys.stderr.write(f"Output: {out_path}\n")
    if errors:
        sys.stderr.write("Failures:\n")
        for row in results:
            if not row.get("pass"):
                reasons = ", ".join(row.get("fail_reasons") or [])
                sys.stderr.write(f"- {row.get('author')}: {reasons}\n")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
